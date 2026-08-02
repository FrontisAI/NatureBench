#!/usr/bin/env python3
"""Compute NatureBench leaderboard metrics from per-case results."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable

from validate_submission import (
    ResultRecord,
    default_case_metadata_path,
    load_case_metadata,
)


def _rounded(value: float | None) -> float | None:
    return round(value, 6) if value is not None else None


def _percentage(count: int, total: int) -> float:
    return round(count / total * 100.0, 6) if total else 0.0


def _mean(values: list[float]) -> float | None:
    return _rounded(statistics.fmean(values)) if values else None


def _median(values: list[float]) -> float | None:
    return _rounded(statistics.median(values)) if values else None


def _require_judge_verdicts(records: Iterable[ResultRecord]) -> None:
    missing = [record.case_id for record in records if not record.judge_verdict.strip()]
    if missing:
        raise ValueError(
            "judge_verdict must be non-empty for every case; missing for: "
            + ", ".join(missing)
        )


def load_scoring_results(
    path: Path,
    case_metadata: dict[str, str],
) -> dict[str, ResultRecord]:
    """Load only the result fields required to calculate leaderboard metrics."""

    records: dict[str, ResultRecord] = {}
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            required_fields = {"case_id", "best_score", "judge_verdict"}
            missing_fields = required_fields - set(reader.fieldnames or [])
            if missing_fields:
                raise ValueError(
                    f"{path}: missing required columns: "
                    + ", ".join(sorted(missing_fields))
                )

            for line_number, row in enumerate(reader, start=2):
                case_id = (row.get("case_id") or "").strip()
                if not case_id:
                    raise ValueError(f"{path}:{line_number}: case_id is empty")
                if case_id in records:
                    raise ValueError(f"{path}:{line_number}: duplicate case_id {case_id}")

                raw_score = (row.get("best_score") or "").strip()
                if raw_score:
                    try:
                        best_score = float(raw_score)
                    except ValueError as error:
                        raise ValueError(
                            f"{path}:{line_number}: best_score must be numeric or empty"
                        ) from error
                    if not math.isfinite(best_score):
                        raise ValueError(
                            f"{path}:{line_number}: best_score must be finite"
                        )
                else:
                    best_score = None

                records[case_id] = ResultRecord(
                    case_id=case_id,
                    final_status=(row.get("final_status") or "").strip(),
                    best_score=best_score,
                    judge_verdict=(row.get("judge_verdict") or "").strip().lower(),
                    judge_reason=(
                        row.get("judge_reason")
                        or row.get("judge_invalid_reason")
                        or ""
                    ).strip(),
                )
    except OSError as error:
        raise ValueError(f"cannot read results file {path}: {error}") from error

    expected_cases = set(case_metadata)
    actual_cases = set(records)
    missing_cases = sorted(expected_cases - actual_cases)
    unknown_cases = sorted(actual_cases - expected_cases)
    if missing_cases or unknown_cases:
        details: list[str] = []
        if missing_cases:
            details.append(
                f"missing {len(missing_cases)} official cases: {', '.join(missing_cases)}"
            )
        if unknown_cases:
            details.append(
                f"contains {len(unknown_cases)} unknown cases: {', '.join(unknown_cases)}"
            )
        raise ValueError(f"{path}: " + "; ".join(details))
    return records


def calculate_metrics(records: list[ResultRecord]) -> dict[str, Any]:
    """Calculate metrics for one complete benchmark or domain subset."""

    _require_judge_verdicts(records)
    total = len(records)
    scored = [record for record in records if record.best_score is not None]
    valid = [record for record in scored if record.judge_verdict == "valid"]
    invalid = [record for record in scored if record.judge_verdict == "invalid"]
    no_score = [record for record in records if record.best_score is None]

    valid_scores = [record.best_score for record in valid if record.best_score is not None]
    all_scores = [
        record.best_score
        if record.best_score is not None and record.judge_verdict == "valid"
        else -1.0
        for record in records
    ]

    distribution = {
        "no_score": len(no_score),
        "invalid": len(invalid),
        "g_lt_minus_0_5": sum(score < -0.5 for score in valid_scores),
        "g_minus_0_5_to_0": sum(-0.5 <= score < 0 for score in valid_scores),
        "g_0_to_0_1": sum(0 <= score <= 0.1 for score in valid_scores),
        "g_0_1_to_0_5": sum(0.1 < score <= 0.5 for score in valid_scores),
        "g_gt_0_5": sum(score > 0.5 for score in valid_scores),
    }

    return {
        "task_count": total,
        "scored_count": len(scored),
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "no_score_count": len(no_score),
        "score_rate": _percentage(len(scored), total),
        "completion_rate": _percentage(len(valid), total),
        "match_sota": _percentage(sum(score >= 0 for score in valid_scores), total),
        "surpass_sota": _percentage(sum(score > 0.1 for score in valid_scores), total),
        "mean_g_all": _mean(all_scores),
        "median_g_all": _median(all_scores),
        "median_g_valid": _median(valid_scores),
        "distribution": distribution,
    }


def calculate_report(
    records: dict[str, ResultRecord],
    case_metadata: dict[str, str],
) -> dict[str, Any]:
    ordered_records = [records[case_id] for case_id in sorted(case_metadata)]
    _require_judge_verdicts(ordered_records)
    domains: dict[str, dict[str, Any]] = {}
    for domain in sorted(set(case_metadata.values())):
        domain_records = [
            records[case_id]
            for case_id in sorted(case_metadata)
            if case_metadata[case_id] == domain
        ]
        domains[domain] = calculate_metrics(domain_records)
    return {
        "metric_version": "naturebench-public-v1",
        "overall": calculate_metrics(ordered_records),
        "domains": domains,
    }


def _display(value: Any, percent: bool = False) -> str:
    if value is None:
        return "n/a"
    if percent:
        return f"{value:.2f}%"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def format_summary(report: dict[str, Any]) -> str:
    overall = report["overall"]
    rows = [
        ("Score Rate (SR)", _display(overall["score_rate"], percent=True)),
        ("Completion Rate (CR)", _display(overall["completion_rate"], percent=True)),
        ("Match-SOTA", _display(overall["match_sota"], percent=True)),
        ("Surpass-SOTA", _display(overall["surpass_sota"], percent=True)),
        ("Mean g (all)", _display(overall["mean_g_all"])),
        ("Median g (all)", _display(overall["median_g_all"])),
        ("Median g (valid)", _display(overall["median_g_valid"])),
        ("Invalid", str(overall["invalid_count"])),
        ("No score", str(overall["no_score_count"])),
    ]
    width = max(len(label) for label, _ in rows)
    lines = ["NatureBench score preview"]
    lines.extend(f"{label:<{width}}  {value}" for label, value in rows)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True, help="results.csv")
    parser.add_argument("--output", type=Path, help="optional score_report.json")
    parser.add_argument(
        "--case-metadata",
        type=Path,
        default=default_case_metadata_path(),
        help="official case metadata CSV",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        case_metadata = load_case_metadata(args.case_metadata)
        records = load_scoring_results(args.results, case_metadata)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    try:
        report = calculate_report(records, case_metadata)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(format_summary(report))
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as error:
            print(f"ERROR: cannot write {args.output}: {error}", file=sys.stderr)
            return 1
        print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
