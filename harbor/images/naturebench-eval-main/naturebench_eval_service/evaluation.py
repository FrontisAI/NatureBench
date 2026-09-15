from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .scoring import compute_improvements, load_primary_table
from .timer import EffectiveTimer

logger = logging.getLogger("naturebench.sidecar")
RESULT_MARKER = "===EVAL_RESULT_JSON==="


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, default=str)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def run_evaluator_subprocess(evaluation_dir: Path, output_dir: Path) -> dict[str, Any]:
    evaluator = evaluation_dir / "evaluator.py"
    runner = Path(__file__).with_name("evaluator_runner.py")
    environment = {**os.environ, "OUTPUT_DIR": str(output_dir)}
    try:
        process = subprocess.run(
            [sys.executable, str(runner), str(evaluator)],
            env=environment,
            capture_output=True,
            text=True,
            timeout=3600,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("evaluator timed out after 3600 seconds") from error
    if process.returncode != 0:
        raise RuntimeError(
            f"evaluator failed with exit {process.returncode}: {(process.stderr or '')[-1500:]}"
        )
    stdout = process.stdout or ""
    marker_index = stdout.rfind(RESULT_MARKER)
    if marker_index < 0:
        raise RuntimeError("evaluator produced no result marker")
    result = json.loads(stdout[marker_index + len(RESULT_MARKER) :].strip())
    return result if isinstance(result, dict) else {}


class SingleTrialEvaluator:
    def __init__(
        self,
        task_name: str,
        metadata_path: Path,
        output_dir: Path,
        state_dir: Path,
        evaluation_dir: Path | None = None,
        evaluator: Callable[[Path], dict[str, Any]] | None = None,
    ) -> None:
        self.task_name = task_name
        self.output_dir = output_dir
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.primary_table = load_primary_table(metadata_path)
        self.timer = EffectiveTimer()
        self._state_lock = threading.RLock()
        self._persistence_lock = threading.Lock()
        self._submissions: list[dict[str, Any]] = []
        self._best: dict[str, Any] | None = None
        with self.submissions_path.open("a", encoding="utf-8") as stream:
            stream.flush()
            os.fsync(stream.fileno())
        if evaluator is not None:
            self._evaluator = evaluator
        elif evaluation_dir is not None:
            self._evaluator = lambda output: run_evaluator_subprocess(evaluation_dir, output)
        else:
            raise ValueError("evaluation_dir or evaluator is required")

    @property
    def submissions_path(self) -> Path:
        return self.state_dir / "submissions.jsonl"

    @property
    def best_score_path(self) -> Path:
        return self.state_dir / "best_score.json"

    def best_score_payload(self, finalized: bool = False) -> dict[str, Any]:
        with self._state_lock:
            best = self._best or {}
            return {
                "status": "scored" if self._best is not None else "no_score",
                "finalized": finalized,
                "best_attempt": best.get("attempt"),
                "best_aggregate_improvement": best.get("aggregate_improvement"),
                "best_per_instance_improvement": best.get("per_instance_improvement", {}),
                "best_raw_scores": best.get("raw_scores", {}),
                "total_attempts": len(self._submissions),
                "updated_at": utc_now(),
            }

    def _append_submission(self, record: dict[str, Any]) -> None:
        self.submissions_path.parent.mkdir(parents=True, exist_ok=True)
        with self.submissions_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _persist_current_state(self, record: dict[str, Any]) -> None:
        with self._persistence_lock:
            try:
                self._append_submission(record)
                atomic_write_json(self.best_score_path, self.best_score_payload())
            except OSError as error:
                logger.warning("state persistence failed; response remains valid: %s", error)

    def evaluate(self) -> dict[str, Any]:
        self.timer.begin_evaluation()
        try:
            raw_scores = self._evaluator(self.output_dir)
            per_instance, aggregate = compute_improvements(raw_scores, self.primary_table)
            attempt = len(self._submissions) + 1
            with self._state_lock:
                record = {
                    "type": "success",
                    "attempt": attempt,
                    "timestamp": time.time(),
                    "raw_scores": raw_scores,
                    "per_instance_improvement": per_instance,
                    "aggregate_improvement": aggregate,
                }
                self._submissions.append(record)
                if aggregate is not None and (
                    self._best is None
                    or aggregate > self._best["aggregate_improvement"]
                ):
                    self._best = record
            self._persist_current_state(record)
            return {
                "attempt": attempt,
                "raw_scores": raw_scores,
                "per_instance_improvement": per_instance,
                "aggregate_improvement": aggregate,
                "best_aggregate_improvement": self._best["aggregate_improvement"] if self._best else None,
                "best_attempt": self._best["attempt"] if self._best else None,
            }
        except Exception as error:
            attempt = len(self._submissions) + 1
            with self._state_lock:
                record = {
                    "type": "failure",
                    "attempt": attempt,
                    "timestamp": time.time(),
                    "raw_scores": None,
                    "per_instance_improvement": None,
                    "aggregate_improvement": None,
                    "error": str(error),
                }
                self._submissions.append(record)
            self._persist_current_state(record)
            raise
        finally:
            self.timer.end_evaluation()
