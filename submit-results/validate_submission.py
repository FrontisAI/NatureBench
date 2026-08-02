#!/usr/bin/env python3
"""Validate a NatureBench leaderboard submission package."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import yaml


RESULT_FIELDS = [
    "case_id",
    "final_status",
    "best_score",
    "judge_verdict",
    "judge_reason",
]
SUBMISSION_FIELDS = {
    "model",
    "agent",
    "organization",
    "url",
    "submission_date",
    "contact",
}
EVALUATION_FIELDS = {
    "timeout_seconds",
    "web_search",
    "compute",
    "judge_model",
    "human_intervention",
    "deviations_from_reference",
}
SCORE_TOLERANCE = 1e-9


@dataclass(frozen=True)
class ResultRecord:
    """Normalized values from one results.csv row."""

    case_id: str
    final_status: str
    best_score: float | None
    judge_verdict: str
    judge_reason: str


@dataclass
class ValidationReport:
    """Collect validation errors and non-blocking review warnings."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def default_case_metadata_path() -> Path:
    return Path(__file__).with_name("case_metadata.csv")


def load_case_metadata(path: Path) -> dict[str, str]:
    """Load the official case-to-domain mapping."""

    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not {"case_id", "domain"}.issubset(reader.fieldnames or []):
                raise ValueError(f"{path}: missing case_id or domain column")
            cases = {
                (row.get("case_id") or "").strip():
                (row.get("domain") or "").strip()
                for row in reader
            }
    except OSError as error:
        raise ValueError(f"cannot read case metadata {path}: {error}") from error
    return cases


def _nonempty_string(
    mapping: dict[str, Any],
    key: str,
    location: str,
    report: ValidationReport,
) -> None:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        report.error(f"{location}.{key} must be a non-empty string")


def _check_exact_keys(
    mapping: dict[str, Any],
    expected: set[str],
    location: str,
    report: ValidationReport,
) -> None:
    missing = sorted(expected - set(mapping))
    extra = sorted(set(mapping) - expected)
    if missing:
        report.error(f"{location} is missing fields: {', '.join(missing)}")
    if extra:
        report.error(f"{location} has unsupported fields: {', '.join(extra)}")


def validate_metadata(path: Path, report: ValidationReport) -> dict[str, Any] | None:
    """Validate submission.yaml and return its parsed mapping."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        report.error(f"cannot read metadata file {path}: {error}")
        return None
    except yaml.YAMLError as error:
        report.error(f"invalid YAML in {path}: {error}")
        return None

    if not isinstance(payload, dict):
        report.error(f"{path} must contain a YAML mapping")
        return None
    _check_exact_keys(payload, {"submission", "evaluation"}, "metadata", report)

    submission = payload.get("submission")
    if not isinstance(submission, dict):
        report.error("metadata.submission must be a mapping")
    else:
        _check_exact_keys(submission, SUBMISSION_FIELDS, "submission", report)
        for key in ("model", "agent", "organization", "url", "contact"):
            _nonempty_string(submission, key, "submission", report)
        url = submission.get("url")
        if isinstance(url, str) and url.strip():
            parsed_url = urlparse(url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                report.error("submission.url must be a complete http:// or https:// URL")
        submitted = submission.get("submission_date")
        if not isinstance(submitted, str):
            report.error("submission.submission_date must use YYYY-MM-DD")
        else:
            try:
                date.fromisoformat(submitted)
            except ValueError:
                report.error("submission.submission_date must use YYYY-MM-DD")

    evaluation = payload.get("evaluation")
    if not isinstance(evaluation, dict):
        report.error("metadata.evaluation must be a mapping")
    else:
        _check_exact_keys(evaluation, EVALUATION_FIELDS, "evaluation", report)
        timeout = evaluation.get("timeout_seconds")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            report.error("evaluation.timeout_seconds must be a positive integer")
        if not isinstance(evaluation.get("web_search"), bool):
            report.error("evaluation.web_search must be true or false")
        for key in ("compute", "human_intervention", "deviations_from_reference"):
            _nonempty_string(evaluation, key, "evaluation", report)
        judge_model = evaluation.get("judge_model")
        if not isinstance(judge_model, str):
            report.error("evaluation.judge_model must be a string; use an empty string if unused")

    return payload


def _parse_score(
    raw_value: str,
    case_id: str,
    report: ValidationReport,
) -> float | None:
    value = raw_value.strip()
    if not value:
        return None
    try:
        score = float(value)
    except ValueError:
        report.error(
            f"results.csv {case_id}: best_score must be numeric or empty, got {value!r}"
        )
        return None
    if not math.isfinite(score):
        report.error(
            f"results.csv {case_id}: best_score must be finite; do not use NaN or infinity"
        )
        return None
    return score


def load_results_csv(
    path: Path,
    case_metadata: dict[str, str],
    report: ValidationReport,
) -> dict[str, ResultRecord]:
    """Parse and validate results.csv."""

    records: dict[str, ResultRecord] = {}
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != RESULT_FIELDS:
                report.error(
                    f"{path}: expected columns {RESULT_FIELDS}, got {reader.fieldnames}"
                )
                return records
            for line_number, row in enumerate(reader, start=2):
                case_id = (row.get("case_id") or "").strip()
                if not case_id:
                    report.error(f"{path}:{line_number}: case_id is empty")
                    continue
                if case_id in records:
                    report.error(f"{path}:{line_number}: duplicate case_id {case_id}")
                    continue

                final_status = (row.get("final_status") or "").strip()
                if not final_status:
                    report.error(f"results.csv {case_id}: final_status is required")
                score = _parse_score(row.get("best_score") or "", case_id, report)
                verdict = (row.get("judge_verdict") or "").strip().lower()
                reason = (row.get("judge_reason") or "").strip()

                if not verdict:
                    report.error(f"results.csv {case_id}: judge_verdict is required")
                elif score is not None and verdict not in {"valid", "invalid"}:
                    report.error(
                        f"results.csv {case_id}: a scored result requires judge_verdict "
                        "valid or invalid"
                    )
                elif score is None and verdict not in {"valid", "invalid", "not_applicable"}:
                    report.error(
                        f"results.csv {case_id}: an unscored result requires judge_verdict "
                        "valid, invalid, or not_applicable"
                    )
                if not reason:
                    report.error(f"results.csv {case_id}: judge_reason is required")
                if verdict == "not_applicable" and reason != "not_applicable":
                    report.error(
                        f"results.csv {case_id}: judge_reason must be not_applicable "
                        "when judge_verdict is not_applicable"
                    )

                records[case_id] = ResultRecord(
                    case_id=case_id,
                    final_status=final_status,
                    best_score=score,
                    judge_verdict=verdict,
                    judge_reason=reason,
                )
    except OSError as error:
        report.error(f"cannot read results file {path}: {error}")
        return records

    expected = set(case_metadata)
    actual = set(records)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        report.error(f"results.csv is missing {len(missing)} official cases: {', '.join(missing)}")
    if unknown:
        report.error(f"results.csv contains {len(unknown)} unknown cases: {', '.join(unknown)}")
    return records


def _read_json(path: Path, report: ValidationReport) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        report.error(f"cannot read {path}: {error}")
    except json.JSONDecodeError as error:
        report.error(f"invalid JSON in {path}: {error}")
    return None


def _read_jsonl(path: Path, report: ValidationReport) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as error:
        report.error(f"cannot read {path}: {error}")
        return records
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            report.error(f"invalid JSONL in {path}:{line_number}: {error}")
            continue
        if not isinstance(value, dict):
            report.error(f"{path}:{line_number}: each JSONL record must be an object")
            continue
        records.append(value)
    return records


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _scores_equal(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=SCORE_TOLERANCE, abs_tol=SCORE_TOLERANCE)


def _validate_status(
    case_id: str,
    record: ResultRecord,
    task_result: Any,
    report: ValidationReport,
) -> None:
    if not isinstance(task_result, dict):
        return
    status = task_result.get("status")
    if isinstance(status, str) and status != record.final_status:
        report.error(
            f"{case_id}: final_status {record.final_status!r} does not match "
            f"result.json status {status!r}"
        )


def _validate_scores(
    case_id: str,
    record: ResultRecord,
    attempts: list[dict[str, Any]],
    report: ValidationReport,
) -> None:
    scored_attempts: list[float] = []
    for value in attempts:
        score = _finite_number(value.get("aggregate_improvement"))
        if score is not None:
            scored_attempts.append(score)

    if record.best_score is None:
        if scored_attempts:
            report.error(
                f"{case_id}: results.csv has no score but submissions.jsonl contains "
                f"{len(scored_attempts)} scored attempts"
            )
        return

    if not scored_attempts:
        report.error(f"{case_id}: numeric best_score has no scored attempt in submissions.jsonl")
        return

    best_score = max(scored_attempts)
    if not _scores_equal(record.best_score, best_score):
        report.error(
            f"{case_id}: results.csv best_score {record.best_score} does not match "
            f"submissions.jsonl maximum {best_score}"
        )


def _validate_judge(
    case_id: str,
    record: ResultRecord,
    path: Path,
    report: ValidationReport,
) -> None:
    if record.judge_verdict not in {"valid", "invalid"}:
        return
    if not path.is_file():
        report.error(f"{case_id}: judge_verdict.json is required for a submitted verdict")
        return
    value = _read_json(path, report)
    if not isinstance(value, dict):
        return
    expected = record.judge_verdict == "valid"
    if value.get("is_valid") is not expected:
        report.error(
            f"{case_id}: results.csv verdict {record.judge_verdict!r} does not match "
            f"judge_verdict.json is_valid={value.get('is_valid')!r}"
        )
    reason = value.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        report.error(f"{case_id}: judge_verdict.json reason must be a non-empty string")
    elif reason.strip() != record.judge_reason:
        report.error(f"{case_id}: judge_reason does not match judge_verdict.json reason")


def _validate_trajectories(task_dir: Path, case_id: str, report: ValidationReport) -> None:
    trajectories = sorted(
        path for path in task_dir.glob("trajectory.*") if path.is_file()
    )
    if not trajectories:
        report.error(f"{case_id}: at least one trajectory.* file is required")
        return
    for path in trajectories:
        try:
            with path.open("rb") as handle:
                if not handle.read(1):
                    report.error(f"{case_id}: trajectory file is empty: {path.name}")
        except OSError as error:
            report.error(f"{case_id}: cannot read trajectory file {path.name}: {error}")


def validate_raw_results(
    raw_results: Path,
    records: dict[str, ResultRecord],
    case_metadata: dict[str, str],
    report: ValidationReport,
) -> None:
    """Validate the common per-case raw-results structure."""

    if not raw_results.is_dir():
        report.error(f"raw results directory does not exist: {raw_results}")
        return

    for case_id in sorted(case_metadata):
        record = records.get(case_id)
        if record is None:
            continue
        task_dir = raw_results / case_id
        if not task_dir.is_dir():
            report.error(f"{case_id}: raw-results case directory is missing")
            continue

        result_path = task_dir / "result.json"
        submissions_path = task_dir / "submissions.jsonl"

        for required_path in (result_path, submissions_path):
            if not required_path.is_file():
                report.error(f"{case_id}: required file is missing: {required_path.name}")

        task_result = _read_json(result_path, report) if result_path.is_file() else None
        _validate_status(case_id, record, task_result, report)
        attempts = _read_jsonl(submissions_path, report) if submissions_path.is_file() else []
        _validate_scores(case_id, record, attempts, report)
        _validate_judge(
            case_id,
            record,
            task_dir / "judge_verdict.json",
            report,
        )
        _validate_trajectories(task_dir, case_id, report)


def format_report(report: ValidationReport) -> str:
    lines: list[str] = []
    for message in report.errors:
        lines.append(f"ERROR: {message}")
    for message in report.warnings:
        lines.append(f"WARNING: {message}")
    if report.ok:
        lines.append(
            f"PASS: validation completed with {len(report.warnings)} warning(s) and no errors"
        )
    else:
        lines.append(
            f"FAIL: validation found {len(report.errors)} error(s) and "
            f"{len(report.warnings)} warning(s)"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True, help="submission.yaml")
    parser.add_argument("--results", type=Path, required=True, help="results.csv")
    parser.add_argument(
        "--raw-results",
        type=Path,
        required=True,
        help="raw-results directory",
    )
    parser.add_argument(
        "--case-metadata",
        type=Path,
        default=default_case_metadata_path(),
        help="official case metadata CSV",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = ValidationReport()
    try:
        case_metadata = load_case_metadata(args.case_metadata)
    except ValueError as error:
        report.error(str(error))
        print(format_report(report))
        return 1

    validate_metadata(args.metadata, report)
    records = load_results_csv(args.results, case_metadata, report)
    validate_raw_results(args.raw_results, records, case_metadata, report)
    print(format_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
