#!/usr/bin/env python3
"""Shared sequential-per-paper pipeline, CSV checkpoints and bounded repair loops.

Entry points: batch_pipeline_main.py and batch_pipeline_verified.py.
Only the Python standard library is required by this orchestrator.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone

if __package__:
    from .batch_target_utils import add_target_arguments, resolve_targets
else:
    from batch_target_utils import add_target_arguments, resolve_targets


ROOT = Path(__file__).resolve().parent.parent
STAGES = (
    "preprocess", "paper_filter", "filter_verify", "data_check",
    "data_verify", "task_build", "task_verify", "docker_verify",
)
FIELDS = ("paper_id", "paper_path", "completed", "current_stage", "end_stage", *STAGES)
DONE = {"pass", "pass_with_warnings", "pending_review"}
STATUSES = DONE | {"", "fail", "error", "skipped_upstream", "skipped_disabled"}
FIXES = {
    "filter_verify": "filter_apply", "data_verify": "data_apply",
    "task_verify": "task_fix", "docker_verify": "docker_fix",
}
# Action -> existing batch driver / fixed log stem / primary output.
ACTIONS = {
    "preprocess": ("batch_paper_preprocess.py", "paper_preprocess", "preprocessed/text.md"),
    "paper_filter": ("batch_paper_filter.py", "paper_filter", "filter_result.json"),
    "filter_verify": ("batch_filter_verify.py", "filter_verify", "verification_result.json"),
    "filter_apply": ("batch_filter_verify_correction.py", "filter_verify_correction", "filter_verify_apply_log.txt"),
    "data_check": ("batch_data_check.py", "data_check", "filter_result.json"),
    "data_verify": ("batch_data_verify.py", "data_verify", "data_verify_result.json"),
    "data_apply": ("batch_data_verify_correction.py", "data_verify_correction", "data_verify_apply_log.txt"),
    "task_build": ("batch_task_build.py", "task_build", "filter_result.json"),
    "task_verify": ("batch_task_verify.py", "task_verify", "task_verify_result.json"),
    "task_fix": ("batch_task_fix.py", "task_fix", "task_fix_log.txt"),
    "docker_verify": ("batch_dockerfile_verify.sh", "docker_verify", "environment/verify_result.txt"),
    "docker_fix": ("batch_dockerfile_fix.py", "dockerfile_fix", "environment/dockerfile_fix_log.txt"),
}


@dataclass(frozen=True)
class Options:
    state_file: Path
    verified: bool = False
    docker: bool = False
    max_fix_rounds: int = 2
    docker_max_fix_rounds: int = 2
    agent: str = "claude"
    jobs: int = 1
    resume: bool = False

    def enabled(self, stage: str) -> bool:
        if stage == "docker_verify":
            return self.docker
        return stage not in FIXES or self.verified

    def limit(self, stage: str) -> int:
        return self.docker_max_fix_rounds if stage == "docker_verify" else self.max_fix_rounds


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


class StateTable:
    """One writer lock per CSV, plus a mutex for worker-thread updates."""

    def __init__(self, options: Options):
        self.options = options
        self.path = options.state_file
        self.rows: dict[str, dict[str, str]] = {}
        self.mutex = threading.Lock()

    def __enter__(self) -> StateTable:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file = self.path.with_name(self.path.name + ".lock").open("a")
        try:
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if self.path.exists():
                if not self.options.resume:
                    raise ValueError(f"State CSV already exists; use --resume: {self.path}")
                with self.path.open(newline="", encoding="utf-8") as handle:
                    reader = csv.DictReader(handle)
                    if reader.fieldnames != list(FIELDS):
                        raise ValueError("State CSV has unexpected columns")
                    for row in reader:
                        key = row["paper_path"]
                        if (not key or key in self.rows or row["completed"] not in {"true", "false"}
                                or any(row[s] not in STATUSES for s in STAGES)
                                or any(row[s] not in ("", *STAGES) for s in ("current_stage", "end_stage"))):
                            raise ValueError(f"Invalid or duplicate state CSV row: {key}")
                        self.rows[key] = row
            elif self.options.resume:
                raise ValueError(f"Cannot resume without state CSV: {self.path}")
        except BaseException:
            self.lock_file.close()
            raise
        return self

    def __exit__(self, *_: object) -> None:
        self.lock_file.close()

    def get(self, paper: Path) -> dict[str, str] | None:
        with self.mutex:
            row = self.rows.get(str(paper))
            return dict(row) if row else None

    def save(self, row: dict[str, str]) -> None:
        with self.mutex:
            self.rows[row["paper_path"]] = dict(row)
            temporary = self.path.with_name(self.path.name + ".tmp")
            with temporary.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(self.rows.values())
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(self.path)


class PaperRunner:
    def __init__(self, paper: Path, options: Options, table: StateTable,
                 docker_lock: threading.Lock):
        self.paper = paper
        self.options = options
        self.table = table
        self.docker_lock = docker_lock
        self.event_path = paper / "logs/pipeline_events.jsonl"
        self.events: list[dict] = []
        self.row: dict[str, str] = {}
        self.stage = "preprocess"
        self.validating_completed = False

    def event(self, event: str, **details: object) -> None:
        record = {"time": datetime.now(timezone.utc).isoformat(),
                  "stage": self.stage, "event": event, **details}
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        with self.event_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.events.append(record)

    def used(self, stage: str) -> int:
        return sum(e["event"] == "fix_started" and e.get("stage") == stage for e in self.events)

    def initialize(self) -> None:
        saved = self.table.get(self.paper)
        if self.event_path.exists():
            with self.event_path.open(encoding="utf-8") as handle:
                self.events = [json.loads(line) for line in handle if line.strip()]
            if not self.options.resume:
                raise ValueError(f"Existing pipeline history; resume its original CSV: {self.event_path}")
            if not self.events or self.events[0].get("event") != "initialized":
                raise ValueError(f"Missing initialization/counters: {self.event_path}")
            initial = self.events[0]
            if (initial.get("state_file") != str(self.options.state_file)
                    or initial.get("verified") != self.options.verified):
                raise ValueError("Resume must use the same pipeline version and state file")
        elif saved:
            raise ValueError(f"Cannot recover repair counts: missing {self.event_path}")
        else:
            self.event("initialized", state_file=str(self.options.state_file), verified=self.options.verified)
        self.row = saved or dict.fromkeys(FIELDS, "")
        if not saved:
            self.row.update(paper_id=self.paper.name, paper_path=str(self.paper), completed="false")
        for stage in STAGES:
            if not self.options.enabled(stage):
                # Retain previously obtained Docker results, even when disabled now.
                if self.row[stage] in {"", "error", "skipped_upstream"}:
                    self.row[stage] = "skipped_disabled"
        self.table.save(self.row)

    def reopen(self, stage: str) -> None:
        for downstream in STAGES[STAGES.index(stage):]:
            if self.options.enabled(downstream):
                self.row[downstream] = ""
        previous = [s for s in STAGES[:STAGES.index(stage)] if self.row[s] in DONE]
        self.row.update(completed="false", end_stage="", current_stage=previous[-1] if previous else "")
        self.table.save(self.row)

    def should_run(self) -> bool:
        if self.row["completed"] == "true":
            end = self.row["end_stage"]
            stopped = next((e for e in reversed(self.events)
                            if e["event"] == "stopped" and e.get("stage") == end), None)
            if self.row.get(end) == "fail":
                if (end in FIXES and self.options.enabled(end) and stopped
                        and stopped.get("cause") == "fix_limit"
                        and self.used(end) < self.options.limit(end)):
                    self.reopen(end)
                    return True
                return False
            if self.options.docker and self.row["docker_verify"] == "skipped_disabled":
                self.reopen("docker_verify")
                return True
            return False
        # An earlier invocation may have stopped immediately after updating a failed stage.
        failed = next((s for s in STAGES if self.row[s] == "fail"), None)
        if failed:
            raise ValueError(f"Inconsistent CSV: incomplete pipeline contains terminal failure at {failed}")
        if self.options.docker and self.row["docker_verify"] == "skipped_disabled":
            self.row["docker_verify"] = ""
        return True

    def stamp(self, path: Path) -> tuple[int, int] | None:
        return (path.stat().st_mtime_ns, path.stat().st_size) if path.is_file() else None

    def execute(self, action: str) -> int:
        """Run one existing driver; overridden by tests to avoid real agents/Docker."""
        script = ROOT / "scripts" / ACTIONS[action][0]
        if action == "docker_verify":
            # Serialize actual builds/runs; no additional user-facing concurrency flags.
            with self.docker_lock:
                for name in ("environment/Dockerfile.v3", "environment/packages.json"):
                    if not (self.paper / name).is_file():
                        raise ValueError(f"Missing Docker input: {name}")
                read_json(self.paper / "environment/packages.json")
                result = subprocess.run(["docker", "info"])
                if result.returncode:
                    raise RuntimeError("Docker daemon is unavailable; see terminal output")
                return subprocess.run(
                    ["bash", str(script), "--single", self.paper.name, str(self.paper.parent)],
                    cwd=ROOT,
                ).returncode
        command = [sys.executable, "-B", str(script), "--single", str(self.paper),
                   "--agent", self.options.agent]
        return subprocess.run(command, cwd=ROOT).returncode

    def call(self, action: str) -> None:
        _, _, relative = ACTIONS[action]
        report = self.paper / relative
        before = self.stamp(report)
        self.event("call_started", action=action)
        # Remove stale verifier reports so only newly generated results can pass.
        if action in FIXES and report.exists():
            report.unlink()
        print(f"[{self.paper.name}] {action}", flush=True)
        code = self.execute(action)
        self.event("call_finished", action=action, returncode=code)
        if code:
            raise RuntimeError(f"{action} exited {code}; see terminal output and {self.paper / 'logs'}")
        if not report.is_file():
            raise ValueError(f"{action} did not produce {report}")
        if action != "preprocess" and action not in FIXES and self.stamp(report) == before:
            raise ValueError(f"{action} did not update its output: {report}")

    def business(self, stage: str) -> str:
        if stage == "preprocess":
            if not (self.paper / "preprocessed/text.md").read_text(encoding="utf-8").strip():
                raise ValueError("Empty preprocessed/text.md")
            read_json(self.paper / "preprocessed/links.json")
            for name in ("figures", "tables"):
                if not (self.paper / "preprocessed" / name).is_dir():
                    raise ValueError(f"Missing preprocessed/{name}")
            return "pass"
        data = read_json(self.paper / "filter_result.json")
        if stage == "task_build":
            status = data["task_build"]["status"]
            if status not in {"success", "pending_review", "failed"}:
                raise ValueError(f"Unknown task_build.status: {status}")
            if status != "failed":
                read_json(self.paper / "metadata.json")
                for name in ("problem", "evaluation", "environment"):
                    if not (self.paper / name).is_dir():
                        raise ValueError(f"Missing task package directory: {name}")
            return {"success": "pass", "pending_review": "pending_review", "failed": "fail"}[status]
        key = "passed" if stage == "paper_filter" else "data_check_passed"
        value = data["final_result"][key]
        if not isinstance(value, bool):
            raise ValueError(f"final_result.{key} must be boolean")
        return "pass" if value else "fail"

    def verdict(self, stage: str) -> str:
        path = self.paper / ACTIONS[stage][2]
        if stage == "docker_verify":
            report = path.read_text(encoding="utf-8")
            statuses = [line.removeprefix("status: ").strip() for line in report.splitlines()
                        if line.startswith("status: ")]
            if len(statuses) != 1:
                raise ValueError("Docker report has no unambiguous status")
            if statuses[0] == "all passed":
                return "pass"
            infrastructure = ("cannot connect to the docker daemon", "docker: command not found",
                              "could not select device driver", "permission denied while trying to connect")
            if any(s in report.lower() for s in infrastructure):
                raise RuntimeError("Docker infrastructure error; not a Dockerfile repair")
            if statuses[0] in {"build failed", "has failures"}:
                return "fail"
            raise RuntimeError(f"Docker verification could not complete: {statuses[0]}")
        report = read_json(path)
        if stage == "task_verify":
            overall = report["overall_status"]
            if overall not in {"pass", "failed"}:
                raise ValueError(f"Unknown task verification status: {overall}")
            if overall == "failed" or report["failed_checks"] or report["dynamic_test"]["status"] == "failed":
                return "fail"
            if report["dynamic_test"]["status"] != "pass":
                raise ValueError("Missing/unknown dynamic test status")
            return "pass_with_warnings" if report["warnings"] else "pass"
        checks = report["checks"]
        if not isinstance(checks, list) or not checks:
            raise ValueError("Verification report must contain checks")
        statuses = [check["status"] for check in checks]
        allowed = {"pass", "fail"} if stage == "filter_verify" else {"pass", "fail", "warning"}
        if any(status not in allowed for status in statuses):
            raise ValueError("Unknown verification check status")
        if stage == "filter_verify":
            verdict = report["verdict"]
            if not isinstance(verdict["judgment_correct"], bool):
                raise ValueError("judgment_correct must be boolean")
            corrections = any(check.get("corrections") for check in checks)
            return "fail" if ("fail" in statuses or corrections or verdict["override"] is not None
                              or not verdict["judgment_correct"] or verdict["correction_count"]) else "pass"
        if "fail" in statuses:
            return "fail"
        return "pass_with_warnings" if "warning" in statuses else "pass"

    def sync_business(self, stage: str) -> str:
        parent = {"filter_verify": "paper_filter", "data_verify": "data_check",
                  "task_verify": "task_build", "docker_verify": "task_build"}[stage]
        result = self.business(parent)
        self.row[parent] = result
        # Applying data corrections may also change the paper-level judgment.
        if stage == "data_verify":
            self.row["paper_filter"] = self.business("paper_filter")
            if self.row["paper_filter"] == "fail":
                result = "fail"
        if result != "fail":
            self.table.save(self.row)
        return result

    def stop(self, cause: str) -> None:
        self.event("stopped", cause=cause)
        self.row[self.stage] = "fail"
        self.row.update(completed="true", current_stage=self.stage, end_stage=self.stage)
        for stage in STAGES[STAGES.index(self.stage) + 1:]:
            self.row[stage] = "skipped_upstream" if self.options.enabled(stage) else "skipped_disabled"
        self.table.save(self.row)

    def verify_loop(self) -> str | None:
        stage = self.stage
        while True:
            if self.sync_business(stage) == "fail":
                self.stop("business_rejected")
                return None
            self.call(stage)
            result = self.verdict(stage)
            if self.sync_business(stage) == "fail":
                self.stop("business_rejected")
                return None
            if result in DONE:
                return result
            used = self.used(stage)
            if used >= self.options.limit(stage):
                self.stop("fix_limit")
                return None
            self.event("fix_started", round=used + 1)
            self.call(FIXES[stage])

    def run(self) -> bool:
        try:
            self.initialize()
            if not self.should_run():
                print(f"[{self.paper.name}] skipped; ended at {self.row['end_stage']}", flush=True)
                return True
            for stage in STAGES:
                if not self.options.enabled(stage):
                    continue
                self.stage = stage
                last_error = next((e for e in reversed(self.events)
                                   if e["event"] == "error" and e.get("stage") == stage), {})
                self.validating_completed = (self.row[stage] in DONE or
                                             (self.row[stage] == "error" and last_error.get("validating_completed", False)))
                if self.validating_completed:
                    # Reuse only readable outputs. No hashing or automatic upstream rebuilds.
                    pending = next((s for s in STAGES if self.options.enabled(s)
                                    and self.row[s] not in DONE), None)
                    mutable_parents = {"filter_verify": {"paper_filter"},
                                       "data_verify": {"paper_filter", "data_check"},
                                       "task_verify": {"task_build"}, "docker_verify": {"task_build"}}
                    if stage in mutable_parents.get(pending, set()) and self.used(pending):
                        # An interrupted fix may already have changed the business decision.
                        # Let that verification loop refresh the parent and handle rejection.
                        self.validating_completed = False
                        continue
                    if stage in FIXES:
                        result = self.verdict(stage)
                    else:
                        result = self.business(stage)
                    if result not in DONE:
                        raise ValueError(f"Saved {stage} result no longer agrees with its output")
                    self.row[stage] = result
                    self.table.save(self.row)
                    self.validating_completed = False
                    continue
                if self.row[stage] == "skipped_upstream":
                    raise ValueError(f"Unexpected upstream skip while resuming {stage}")
                self.row[stage] = ""
                self.table.save(self.row)
                if stage in FIXES:
                    result = self.verify_loop()
                    if result is None:
                        return True
                else:
                    self.call(stage)
                    result = self.business(stage)
                    if result == "fail":
                        self.stop("business_rejected")
                        return True
                self.row[stage] = result
                self.row["current_stage"] = stage
                self.table.save(self.row)
                self.event("stage_finished", status=result)
                print(f"[{self.paper.name}] {stage}: {result}", flush=True)
            self.row.update(completed="true", end_stage=self.row["current_stage"])
            self.table.save(self.row)
            self.event("completed")
            return True
        except Exception as error:
            print(f"[{self.paper.name}] ERROR at {self.stage}: {error}", file=sys.stderr, flush=True)
            # Do not overwrite a CSV if initialization/history validation failed.
            if self.row:
                self.event("error", message=str(error), validating_completed=self.validating_completed)
                self.row[self.stage] = "error"
                self.row.update(completed="false", end_stage="")
                self.table.save(self.row)
            return False


def run_pipeline(targets: list[Path], options: Options) -> int:
    with StateTable(options) as table:
        docker_lock = threading.Lock()
        errors = 0
        with ThreadPoolExecutor(max_workers=options.jobs) as pool:
            futures = [pool.submit(PaperRunner(p, options, table, docker_lock).run) for p in targets]
            for count, future in enumerate(as_completed(futures), 1):
                errors += not future.result()
                print(f"Processed {count}/{len(targets)}; execution errors: {errors}; CSV: {options.state_file}", flush=True)
        print(f"Finished. Business rejections/verification failures are recorded as fail in {options.state_file}")
        return 1 if errors else 0


def main(verified: bool = False) -> int:
    parser = argparse.ArgumentParser(description="NatureGym pipeline: " + ("verified" if verified else "main stages"))
    add_target_arguments(parser)
    parser.add_argument("-j", "--jobs", type=int, default=1, help="Concurrent papers; Docker checks are serialized")
    parser.add_argument("--agent", choices=("claude", "codex"), default="claude")
    parser.add_argument("--max-fix-rounds", type=int, default=2, help="Lifetime repairs per paper per verification stage (default: 2)")
    parser.add_argument("--docker", action=argparse.BooleanOptionalAction, default=verified,
                        help="Enable stage 5 (default: on for verified, off for main)")
    parser.add_argument("--docker-max-fix-rounds", type=int, default=2)
    parser.add_argument("--state-file", type=Path, help="CSV path (default: <input>/pipeline_status.csv)")
    parser.add_argument("--resume", action="store_true", help="Resume the same version using the CSV and per-paper event logs")
    parser.add_argument("--dry-run", action="store_true", help="Print targets/stages without writes or external calls")
    args = parser.parse_args()
    if args.jobs < 1 or min(args.max_fix_rounds, args.docker_max_fix_rounds) < 0:
        parser.error("jobs must be positive; repair limits must be nonnegative")
    try:
        targets, summary = resolve_targets(args.path, single=args.single, start=args.start, end=args.end, sort=args.sort)
        targets = [Path(p).resolve() for p in targets]
        if len(set(targets)) != len(targets):
            raise ValueError("Multiple targets resolve to the same paper directory")
        state = (args.state_file or Path(args.path) / "pipeline_status.csv").resolve()
        options = Options(state, verified, args.docker, args.max_fix_rounds,
                          args.docker_max_fix_rounds, args.agent, args.jobs, args.resume)
        print(summary)
        print("Stages: " + " → ".join(s for s in STAGES if options.enabled(s)))
        print(f"Repair limits: filter/data/task={options.max_fix_rounds}, Docker={options.docker_max_fix_rounds}")
        print(f"State: {state}")
        if args.dry_run:
            for target in targets:
                print(target)
            return 0
        return run_pipeline(targets, options)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
