"""eval_service.py — host-side Evaluation Service (HTTP)

Provides a scoring interface for the solver agent running inside a task
container. The agent produces result files in the container and calls this
service over HTTP to get scores, iterating as many times as needed.

Endpoints:
    POST /evaluate      — submit predictions and return scores
    POST /register      — register a task dynamically
    POST /start_timer   — signal that a task's timer should start (solve.py calls this before launching the agent)
    GET  /best_score    — query the current best score for a task
    GET  /time_remaining — query remaining time
    GET  /health        — health check
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import re
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

# ---- skip-eval threshold (added 2026-04-30) ----------------------------------
# Set high enough to disable the auto-skip; allow override via env var if needed.
import os as _os
CONSEC_FAIL_SKIP_THRESHOLD = int(_os.environ.get("EVAL_SERVICE_CONSEC_FAIL_THRESHOLD", "99999"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [EvalService] %(levelname)s %(message)s",
)
logger = logging.getLogger("eval_service")


# ---------------------------------------------------------------------------
# Score tracking
# ---------------------------------------------------------------------------

@dataclass
class SubmissionRecord:
    """A single submission record."""
    attempt: int
    raw_scores: Dict[str, Any]                     # full nested dict returned by the evaluator
    per_instance_improvement: Dict[str, float]     # {instance: improvement}
    aggregate_improvement: Optional[float]         # mean of per_instance, None if all missing


@dataclass
class TaskState:
    """Evaluation state for a single task."""
    task_name: str
    data_dir: Path                          # task package root directory
    out_dir: Optional[Path] = None          # host output directory (for writing submissions.jsonl)
    primary_table: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # per-instance primary info
    submissions: List[SubmissionRecord] = field(default_factory=list)
    best_attempt: Optional[int] = None
    best_aggregate_improvement: Optional[float] = None
    start_time: Optional[float] = None      # task start time (time.time())
    timeout: Optional[int] = None           # task timeout in seconds
    lock: threading.Lock = field(default_factory=threading.Lock)
    # ---- pause the timer during evaluation ----
    total_paused: float = 0.0               # cumulative paused seconds
    active_evals: int = 0                   # current concurrent evaluations (>0 means paused)
    pause_start: Optional[float] = None     # start time of the current pause
    # ---- auto-skip on consecutive failures ----
    consecutive_failures: int = 0           # consecutive evaluation errors
    should_skip: bool = False               # consecutive failures >= threshold, signal solve.py to stop the container

    def pause_timer(self) -> None:
        """Called when an evaluation starts. The first concurrent evaluation records the pause start."""
        with self.lock:
            self.active_evals += 1
            if self.active_evals == 1:
                self.pause_start = time.time()

    def resume_timer(self) -> None:
        """Called when an evaluation ends. The last concurrent evaluation adds the pause duration."""
        with self.lock:
            self.active_evals -= 1
            if self.active_evals == 0 and self.pause_start is not None:
                self.total_paused += time.time() - self.pause_start
                self.pause_start = None

    def get_effective_elapsed(self) -> float:
        """Return the effective elapsed time with pauses subtracted."""
        with self.lock:
            if self.start_time is None:
                return 0.0
            raw = time.time() - self.start_time
            paused = self.total_paused
            if self.pause_start is not None:
                paused += time.time() - self.pause_start
            return max(0.0, raw - paused)

    def record(self, rec: SubmissionRecord) -> None:
        """Record an attempt and update best by max(aggregate_improvement)."""
        with self.lock:
            self.submissions.append(rec)
            if rec.aggregate_improvement is not None:
                if (self.best_aggregate_improvement is None
                        or rec.aggregate_improvement > self.best_aggregate_improvement):
                    self.best_aggregate_improvement = rec.aggregate_improvement
                    self.best_attempt = rec.attempt


class ScoreTracker:
    """Global thread-safe score tracker.

    The state key is a (task_name, batch_name) tuple, so different batches/agents
    running the same task name do not pollute each other. batch_name defaults to
    "default".
    """

    DEFAULT_BATCH = "default"

    def __init__(self) -> None:
        # key: (task_name, batch_name) -> TaskState
        self._tasks: Dict[Tuple[str, str], TaskState] = {}
        self._lock = threading.Lock()

    def register_task(self, task_name: str, data_dir: Path,
                       start_time: Optional[float] = None,
                       timeout: Optional[int] = None,
                       out_dir: Optional[Path] = None,
                       batch_name: Optional[str] = None,
                       force: bool = False) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
        """Register a task.

        Args:
          batch_name: isolation namespace. Same task_name under different batches do not pollute each other.
          force: True → reset start_time/timeout and clear submissions (force rerun);
                 False → keep submissions/best_score if already present; reset timer
                         state only when start_time has not yet been set (first start),
                         otherwise leave the existing timing context untouched
                         (resume-friendly).
        """
        bn = batch_name or self.DEFAULT_BATCH
        key = (task_name, bn)
        with self._lock:
            existing = self._tasks.get(key)
            if existing is not None and not force:
                # Re-register without force: never overwrite live timer state.
                # Only refresh fields that are safe to update on every call.
                if existing.start_time is None:
                    # Timer never started → safe to take incoming start_time/timeout.
                    existing.start_time = start_time
                if timeout is not None:
                    existing.timeout = timeout
                if out_dir is not None:
                    existing.out_dir = out_dir
                # Always clear stale skip flags so next agent run can score.
                existing.consecutive_failures = 0
                existing.should_skip = False
                # Active eval/pause state must not be touched here; if a prior
                # run left active_evals != 0 it is repaired by /resume_timer.
                return (existing.primary_table, [])
            primary_table, issues = _get_per_instance_primaries(
                data_dir / "metadata.json", task_name=task_name,
            )
            self._tasks[key] = TaskState(
                task_name=task_name, data_dir=data_dir,
                start_time=start_time, timeout=timeout,
                out_dir=out_dir,
                primary_table=primary_table,
            )
            return (primary_table, issues)

    def get_task(self, task_name: str, batch_name: Optional[str] = None) -> Optional[TaskState]:
        bn = batch_name or self.DEFAULT_BATCH
        return self._tasks.get((task_name, bn))

    def all_results(self) -> Dict[str, Any]:
        """Return nested dict {batch_name: {task_name: result_dict}}."""
        results: Dict[str, Dict[str, Any]] = {}
        for (task_name, batch_name), state in self._tasks.items():
            best_rec = None
            if state.best_attempt is not None:
                idx = state.best_attempt - 1
                if 0 <= idx < len(state.submissions):
                    best_rec = state.submissions[idx]
            results.setdefault(batch_name, {})[task_name] = {
                "best_attempt": state.best_attempt,
                "best_aggregate_improvement": state.best_aggregate_improvement,
                "best_per_instance_improvement": best_rec.per_instance_improvement if best_rec else {},
                "best_raw_scores": best_rec.raw_scores if best_rec else {},
                "total_attempts": len(state.submissions),
            }
        return results


# ---------------------------------------------------------------------------
# Core evaluation logic
# ---------------------------------------------------------------------------


def _bn_from_query(parsed) -> Optional[str]:
    """Extract batch_name from URL query string, if present."""
    from urllib.parse import parse_qs as _pq
    val = _pq(parsed.query).get("batch_name", [None])[0]
    return val if val else None



# ---------------------------------------------------------------------------
# AutoSOTA-style normalized scoring
# ---------------------------------------------------------------------------

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
_RANGE_RE = re.compile(
    r"^\s*~?\s*([-+]?\d+(?:\.\d+)?)\s*(?:to|-|–|—)\s*~?\s*([-+]?\d+(?:\.\d+)?)\s*$"
)
_BOUND_RE = re.compile(r"^[<>]=?\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)")
_MEAN_RE = re.compile(
    r"\bmean\s*=\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", re.IGNORECASE
)


def _parse_one_score(value: Any, higher_is_better: bool) -> Optional[float]:
    """Parse a SOTA value string to a float point estimate (mean/typical).

    Accepts:
      - plain number: "10.6"
      - mean ± std:   "0.939 ± 0.002"   → 0.939
      - mean (std):   "11.5 (0.6)"      → 11.5
      - approximate:  "~0.734 ± 0.008"  → 0.734
      - range:        "~0.60 to ~0.95"  → higher_is_better ? 0.95 : 0.60
                      "0.85-0.97"       → same rule
      - bound:        "< 1.6"           → 1.6 (uses the bound itself)
      - explicit mean: "..., (mean=0.919)" → 0.919

    Returns None if no numeric point can be extracted.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    # 1) explicit "mean=X" (handles cases like "..., (mean=0.919)")
    m = _MEAN_RE.search(s)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    # 2) Drop any parenthetical tail — usually stdev or narrative context.
    head = s.split("(")[0].strip()
    # 3) Strip leading "~" (approximate marker)
    core = head.lstrip("~").strip()
    # 4) Range "A to B" or "A-B": pick by direction (best of the range)
    rm = _RANGE_RE.match(core)
    if rm:
        try:
            lo = float(rm.group(1))
            hi = float(rm.group(2))
            return hi if higher_is_better else lo
        except ValueError:
            pass
    # 5) "< 1.6" / ">= 0.9" etc.: use the bound itself
    bm = _BOUND_RE.match(core)
    if bm:
        try:
            return float(bm.group(1))
        except ValueError:
            pass
    # 6) mean ± std: drop everything from the first ± onward
    if "±" in core:
        core = core.split("±", 1)[0].strip().lstrip("~").strip()
    # 7) Fallback: take the first leading float in the string
    nm = _NUM_RE.match(core)
    if nm:
        try:
            return float(nm.group(0))
        except ValueError:
            pass
    return None


def _best_sota(sota_score: Any, higher_is_better: bool) -> Optional[float]:
    """Extract the strongest value by direction from the sota_score field.

    sota_score may be a list / single dict / scalar / non-numeric string.
    Each candidate is parsed by _parse_one_score (supports ±, (…), ~, <, ranges, etc.);
    higher_is_better=True takes the max; False takes the min.
    """
    candidates: List[float] = []

    def _handle(item: Any) -> None:
        if item is None:
            return
        if isinstance(item, dict) and "value" in item:
            v = _parse_one_score(item["value"], higher_is_better)
        else:
            v = _parse_one_score(item, higher_is_better)
        if v is not None:
            candidates.append(v)

    if isinstance(sota_score, list):
        for item in sota_score:
            _handle(item)
    else:
        _handle(sota_score)
    if not candidates:
        return None
    return max(candidates) if higher_is_better else min(candidates)


def _get_per_instance_primaries(
    metadata_path: Path, task_name: Optional[str] = None,
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """Extract the primary metric info for each performance entry from metadata.json.

    Returns:
        (table, issues):
          table = {instance_name: {"metric", "higher_is_better", "sota"}}
          issues = textual list of specific problems (logged as warnings at registration)
        Instances missing sota_score, missing an is_primary metric, or with an
        unparsable sota are not added to the table.
    """
    issues: List[str] = []
    if not metadata_path.exists():
        issues.append(f"metadata.json does not exist: {metadata_path}")
        return ({}, issues)
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        issues.append(f"metadata.json failed to parse: {e}")
        return ({}, issues)
    table: Dict[str, Dict[str, Any]] = {}
    entries = metadata.get("performance_entries", [])
    if not entries:
        issues.append("metadata.performance_entries is empty")
        return ({}, issues)
    for entry in entries:
        instance = entry.get("dataset_name") or entry.get("instance_name")
        if not instance:
            issues.append("an entry in performance_entries is missing dataset_name")
            continue
        primary = next(
            (m for m in entry.get("metrics", []) if m.get("is_primary")),
            None,
        )
        if primary is None:
            issues.append(f"instance={instance}: no is_primary metric, skipped")
            continue
        metric_name = primary.get("name")
        if not metric_name:
            issues.append(f"instance={instance}: primary metric missing name, skipped")
            continue
        higher_is_better = primary.get("metric_direction") == "higher_is_better"
        sota = _best_sota(primary.get("sota_score"), higher_is_better)
        if sota is None:
            issues.append(
                f"instance={instance}, metric={metric_name}: sota_score missing or unparsable, skipped"
            )
            continue
        if sota == 0:
            issues.append(
                f"instance={instance}, metric={metric_name}: sota_score=0 cannot be normalized, skipped"
            )
            continue
        table[instance] = {
            "metric": metric_name,
            "higher_is_better": higher_is_better,
            "sota": sota,
        }
    return (table, issues)


def _find_metric_value(scores: Any, target_metric: str) -> Optional[float]:
    """Recursively search a nested dict for a value whose key matches target_metric.

    Name matching is fuzzy (strips _ - spaces, lowercases).
    """
    norm = lambda s: s.lower().replace("_", "").replace(" ", "").replace("-", "")
    target = norm(target_metric)

    def _recurse(obj: Any) -> Optional[float]:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if norm(str(k)) == target and isinstance(v, (int, float)) and not isinstance(v, bool):
                    return float(v)
            for v in obj.values():
                if isinstance(v, dict):
                    r = _recurse(v)
                    if r is not None:
                        return r
        return None

    return _recurse(scores)


def _compute_improvements(
    raw_scores: Dict[str, Any],
    primary_table: Dict[str, Dict[str, Any]],
) -> Tuple[Dict[str, float], Optional[float]]:
    """Compute per-instance improvement and an aggregate score using AutoSOTA-style normalization.

    Per-instance: improvement = direction × (agent − sota) / |sota|
        higher_is_better → direction = +1, else −1
    Aggregation: mean over ALL primary instances. Failed instances (no finite
    score in the per-instance block) are penalized with a fixed
    failure_penalty = -1.0.

    Note: an earlier draft of this function accepted an `instance_history`
    parameter intended to derive a per-task adaptive penalty
    (`min(-1.0, task_internal_worst)`). That code was never wired up — the
    caller never passed history — so the effective penalty was always -1.0.
    The dead branch and parameter were removed from the public evaluation
    pipeline; behavior
    is unchanged from prior batches because the live code path always took
    the -1.0 default.

    BUG FIX (kept from prior version): no global fallback
    `_find_metric_value(raw_scores, ...)` when an instance block has no
    score, which would otherwise cause sibling-instance score leaks
    ("cross-instance leak").

    Returns:
        (per_instance_improvement, aggregate_improvement)
        aggregate_improvement is None only if primary_table is empty.
    """
    import math as _math
    failure_penalty = -1.0

    per_instance: Dict[str, float] = {}
    for instance, info in primary_table.items():
        sota = info["sota"]
        if sota == 0:
            continue
        # Block-only lookup; NO global fallback (fixes cross-instance leak)
        instance_block = raw_scores.get(instance) if isinstance(raw_scores, dict) else None
        score = _find_metric_value(instance_block, info["metric"]) if instance_block is not None else None
        if score is None or not isinstance(score, (int, float)) or isinstance(score, bool) or not _math.isfinite(score):
            per_instance[instance] = failure_penalty
            continue
        direction = 1.0 if info["higher_is_better"] else -1.0
        per_instance[instance] = direction * (score - sota) / abs(sota)
    if not per_instance:
        return ({}, None)
    aggregate = sum(per_instance.values()) / len(per_instance)
    return (per_instance, aggregate)


def run_evaluator(task_data_dir: Path, output_dir: Path) -> Dict[str, Any]:
    """Run the task package's evaluator.py in a subprocess with an isolated os.environ.

    Args:
        task_data_dir: task package root directory (contains evaluation/evaluator.py)
        output_dir: agent output directory (read by the evaluator via the OUTPUT_DIR env var)

    Returns:
        the results dict returned by the evaluator
    """
    import subprocess as _subp

    evaluator_script = task_data_dir / "evaluation" / "evaluator.py"
    if not evaluator_script.exists():
        raise FileNotFoundError(f"evaluator.py not found: {evaluator_script}")

    wrapper = Path(__file__).parent / "_evaluator_runner.py"
    if not wrapper.exists():
        raise FileNotFoundError(f"_evaluator_runner.py not found: {wrapper}")

    # Run the evaluator in a subprocess with its own environment
    sub_env = {**os.environ, "OUTPUT_DIR": str(output_dir)}

    try:
        proc = _subp.run(
            [sys.executable, str(wrapper), str(evaluator_script)],
            env=sub_env,
            capture_output=True,
            text=True,
            timeout=3600,  # 1h cap per evaluator invocation
        )
    except _subp.TimeoutExpired:
        raise RuntimeError(f"evaluator subprocess timed out after 3600s for {evaluator_script}")

    if proc.returncode != 0:
        # Surface the tail of stderr for debugging
        raise RuntimeError(
            f"evaluator subprocess failed (exit {proc.returncode}): "
            f"{(proc.stderr or '')[-1500:]}"
        )

    # Find the JSON after the marker at the end of stdout
    marker = "===EVAL_RESULT_JSON==="
    out = proc.stdout or ""
    idx = out.rfind(marker)
    if idx < 0:
        raise RuntimeError(
            f"evaluator subprocess produced no result marker. "
            f"stdout tail: {out[-500:]} | stderr tail: {(proc.stderr or '')[-500:]}"
        )
    payload = out[idx + len(marker):].strip()
    try:
        results = json.loads(payload)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"evaluator subprocess output not valid JSON: {e}. payload: {payload[:300]}"
        )
    return results if isinstance(results, dict) else {}


# ---------------------------------------------------------------------------
# HTTP request handling
# ---------------------------------------------------------------------------

class EvalRequestHandler(BaseHTTPRequestHandler):
    """Handle evaluation HTTP requests."""

    tracker: ScoreTracker  # injected by the server

    def log_message(self, format, *args):
        logger.info(format, *args)

    def _send_json(self, status: int, data: Any) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length)

    # ----- GET -----

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if parsed.path == "/best_score":
            params = parse_qs(parsed.query)
            task_name = params.get("task_name", [None])[0]
            if not task_name:
                self._send_json(400, {"error": "missing task_name parameter"})
                return
            state = self.tracker.get_task(task_name, batch_name=_bn_from_query(parsed))
            if state is None:
                self._send_json(404, {"error": f"task {task_name} not registered"})
                return
            best_rec = None
            if state.best_attempt is not None:
                idx = state.best_attempt - 1
                if 0 <= idx < len(state.submissions):
                    best_rec = state.submissions[idx]
            self._send_json(200, {
                "task_name": task_name,
                "best_attempt": state.best_attempt,
                "best_aggregate_improvement": state.best_aggregate_improvement,
                "best_per_instance_improvement": best_rec.per_instance_improvement if best_rec else {},
                "best_raw_scores": best_rec.raw_scores if best_rec else {},
                "total_attempts": len(state.submissions),
            })
            return

        if parsed.path == "/time_remaining":
            params = parse_qs(parsed.query)
            task_name = params.get("task_name", [None])[0]
            if not task_name:
                self._send_json(400, {"error": "missing task_name parameter"})
                return
            state = self.tracker.get_task(task_name, batch_name=_bn_from_query(parsed))
            if state is None:
                self._send_json(404, {"error": f"task {task_name} not registered"})
                return
            elapsed = state.get_effective_elapsed()
            remaining = max(0, state.timeout - elapsed) if state.timeout else None
            # Compute the current cumulative pause time (including the ongoing pause)
            cur_paused = state.total_paused
            if state.pause_start is not None:
                cur_paused += time.time() - state.pause_start
            self._send_json(200, {
                "task_name": task_name,
                "elapsed_seconds": round(elapsed, 1),
                "remaining_seconds": round(remaining, 1) if remaining is not None else None,
                "timeout_seconds": state.timeout,
                "is_paused": state.active_evals > 0,
                "total_paused_seconds": round(cur_paused, 1),
                "should_skip": state.should_skip,
                "consecutive_failures": state.consecutive_failures,
            })
            return

        if parsed.path == "/all_results":
            self._send_json(200, self.tracker.all_results())
            return

        self._send_json(404, {"error": "unknown endpoint"})

    # ----- POST -----

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/evaluate":
            self._handle_evaluate()
            return

        if parsed.path == "/register":
            self._handle_register()
            return

        if parsed.path == "/start_timer":
            self._handle_start_timer()
            return

        if parsed.path == "/resume_timer":
            self._handle_resume_timer()
            return

        if parsed.path == "/pause_timer":
            self._handle_pause_timer()
            return

        self._send_json(404, {"error": "unknown endpoint"})

    def _handle_evaluate(self):
        """Handle POST /evaluate

        Request body JSON:
        {
            "task_name": "s42256-020-0209-y",
            "output_dir": "/workspace/output"   // output directory path inside the container
        }

        Since output_dir is a path inside the container, it is accessed via the
        mount mapping. In practice it is simpler to have the agent send the
        result file contents directly.

        Two modes are supported:
        Mode A — pass a file path (the host must be able to access it):
            {"task_name": "...", "output_dir": "/host/path/to/output"}
        Mode B — pass result data (recommended, used inside the container):
            {"task_name": "...", "predictions": {"instance_name": {"sample_id": label, ...}}}
        """
        try:
            body = json.loads(self._read_body())
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"JSON failed to parse: {e}"})
            return

        task_name = body.get("task_name")
        if not task_name:
            self._send_json(400, {"error": "missing task_name"})
            return

        state = self.tracker.get_task(task_name, batch_name=body.get("batch_name") if body else None)
        if state is None:
            self._send_json(404, {"error": f"task {task_name} not registered"})
            return

        # Pause this task's countdown (evaluation time does not count toward agent solve time)
        state.pause_timer()
        try:
            output_dir_str = body.get("output_dir")
            if not output_dir_str:
                self._send_json(400, {"error": "missing output_dir"})
                return

            output_dir = Path(output_dir_str)
            if not output_dir.exists():
                self._send_json(400, {"error": f"output_dir does not exist: {output_dir}"})
                return

            # Call the evaluator
            results = run_evaluator(state.data_dir, output_dir)

            # AutoSOTA-style normalization: per-instance improvement + aggregate
            per_instance_improvement, aggregate_improvement = _compute_improvements(
                results, state.primary_table
            )

            attempt = len(state.submissions) + 1
            rec = SubmissionRecord(
                attempt=attempt,
                raw_scores=results,
                per_instance_improvement=per_instance_improvement,
                aggregate_improvement=aggregate_improvement,
            )
            state.record(rec)

            # ---- Persist to submissions.jsonl ----
            if state.out_dir is not None:
                try:
                    jsonl_path = state.out_dir / "submissions.jsonl"
                    line = json.dumps({
                        "type": "success",
                        "attempt": attempt,
                        "timestamp": time.time(),
                        "raw_scores": results,
                        "per_instance_improvement": per_instance_improvement,
                        "aggregate_improvement": aggregate_improvement,
                    }, ensure_ascii=False, default=str)
                    with open(jsonl_path, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                except OSError as e:
                    logger.warning("[%s] failed to write submissions.jsonl: %s", task_name, e)

            # ---- Track consecutive failures ----
            if aggregate_improvement is None:
                state.consecutive_failures += 1
                logger.warning(
                    "[%s] aggregate_improvement=None (consecutive_failures=%d)",
                    task_name, state.consecutive_failures,
                )
                if state.consecutive_failures >= CONSEC_FAIL_SKIP_THRESHOLD:
                    state.should_skip = True
                    logger.warning(
                        "[%s] %d consecutive evaluations with no valid score, marking should_skip",
                        task_name, state.consecutive_failures,
                    )
            else:
                state.consecutive_failures = 0

            logger.info(
                "[%s] evaluation complete (attempt=%d): aggregate_improvement=%s, best=%s",
                task_name, attempt, aggregate_improvement,
                state.best_aggregate_improvement,
            )

            self._send_json(200, {
                "task_name": task_name,
                "attempt": attempt,
                "raw_scores": results,
                "per_instance_improvement": per_instance_improvement,
                "aggregate_improvement": aggregate_improvement,
                "best_aggregate_improvement": state.best_aggregate_improvement,
                "best_attempt": state.best_attempt,
            })

        except Exception as e:
            logger.error("[%s] evaluation failed: %s", task_name, traceback.format_exc())
            # ---- record() the failure as a SubmissionRecord with aggregate=None ----
            # state.record() guards best_* with `if aggregate is not None`, so a
            # failure record only grows submissions list / total_attempts; it does
            # NOT pollute best_attempt or best_aggregate_improvement.
            failed_attempt = len(state.submissions) + 1
            try:
                state.record(SubmissionRecord(
                    attempt=failed_attempt,
                    raw_scores={},
                    per_instance_improvement={},
                    aggregate_improvement=None,
                ))
            except Exception as _e_rec:
                logger.warning("[%s] state.record(failure) failed: %s", task_name, _e_rec)
            # ---- persist failure to submissions.jsonl (type=failure, scores=None) ----
            if state.out_dir is not None:
                try:
                    jsonl_path = state.out_dir / "submissions.jsonl"
                    line = json.dumps({
                        "type": "failure",
                        "attempt": failed_attempt,
                        "timestamp": time.time(),
                        "raw_scores": None,
                        "per_instance_improvement": None,
                        "aggregate_improvement": None,
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    }, ensure_ascii=False, default=str)
                    with open(jsonl_path, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                except OSError as _e_io:
                    logger.warning("[%s] failed to write submissions.jsonl (failure): %s", task_name, _e_io)
            # ---- Track consecutive failures (exceptions count too) ----
            state.consecutive_failures += 1
            if state.consecutive_failures >= CONSEC_FAIL_SKIP_THRESHOLD:
                state.should_skip = True
                logger.warning(
                    "[%s] %d consecutive evaluation errors, marking should_skip",
                    task_name, state.consecutive_failures,
                )
            self._send_json(500, {
                "error": f"evaluation failed: {e}",
                "traceback": traceback.format_exc(),
            })
        finally:
            # Resume this task's countdown (whether evaluation succeeded or failed)
            state.resume_timer()

    def _handle_register(self):
        """Handle POST /register — register a task dynamically

        Request body JSON:
        {
            "task_name": "s42256-xxx",
            "data_dir": "/full/path/to/task",
            "timeout": 3600           // optional
        }
        """
        try:
            body = json.loads(self._read_body())
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"JSON failed to parse: {e}"})
            return

        task_name = body.get("task_name")
        if not task_name:
            self._send_json(400, {"error": "missing task_name"})
            return

        data_dir_str = body.get("data_dir")
        if not data_dir_str:
            self._send_json(400, {"error": "missing data_dir"})
            return

        data_dir = Path(data_dir_str)
        if not data_dir.exists():
            self._send_json(400, {
                "error": f"data_dir does not exist: {data_dir_str}",
            })
            return

        timeout = body.get("timeout")
        out_dir_str = body.get("out_dir")
        out_dir = Path(out_dir_str) if out_dir_str else None
        if out_dir is not None:
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.warning("[%s] failed to create out_dir (%s): %s", task_name, out_dir, e)
                out_dir = None
        batch_name = body.get("batch_name")
        force = bool(body.get("force", False))
        primary_table, issues = self.tracker.register_task(
            task_name, data_dir, timeout=timeout, out_dir=out_dir,
            batch_name=batch_name, force=force,
        )
        for msg in issues:
            logger.warning("[%s] METADATA: %s", task_name, msg)
        if not primary_table:
            logger.error(
                "[%s] METADATA: no usable instance (missing sota_score / missing primary metric / all empty), "
                "registration refused. Fix metadata.json and rerun.", task_name,
            )
            self._send_json(422, {
                "status": "incomplete_metadata",
                "task_name": task_name,
                "issues": issues,
            })
            return
        logger.info("[%s] task registered dynamically: data_dir=%s, timeout=%s, out_dir=%s, instances=%d",
                    task_name, data_dir, timeout, out_dir, len(primary_table))

        self._send_json(200, {
            "status": "ok",
            "task_name": task_name,
            "data_dir": data_dir_str,
            "out_dir": str(out_dir) if out_dir else None,
            "instances": list(primary_table.keys()),
            "metadata_warnings": issues,
        })

    def _handle_start_timer(self):
        """Handle POST /start_timer — solve.py signals that a task's timer should start

        Request body JSON:
        {
            "task_name": "s42256-xxx"
        }
        """
        try:
            body = json.loads(self._read_body())
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"JSON failed to parse: {e}"})
            return

        task_name = body.get("task_name")
        if not task_name:
            self._send_json(400, {"error": "missing task_name"})
            return

        batch_name = body.get("batch_name")
        state = self.tracker.get_task(task_name, batch_name=batch_name)
        if state is None:
            self._send_json(404, {"error": f"task {task_name} not registered"})
            return

        with state.lock:
            if state.start_time is not None:
                # Already started; ignore the duplicate call
                self._send_json(200, {
                    "status": "already_started",
                    "task_name": task_name,
                    "start_time": state.start_time,
                })
                return
            state.start_time = time.time()

        logger.info("[%s] timer started", task_name)
        self._send_json(200, {
            "status": "ok",
            "task_name": task_name,
            "start_time": state.start_time,
        })

    def _handle_resume_timer(self):
        """Handle POST /resume_timer — solve.py calls this before a resume run.

        Complementary to /start_timer: it requires the task's timer to have
        **already** been started. This call only confirms that the server-side
        task state still exists and clears any active_evals/pause_start left over
        from the previous run; it **never resets** start_time / total_paused
        / submissions / best_score (all of which must continue across the resume).
        """
        try:
            body = json.loads(self._read_body())
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"JSON failed to parse: {e}"})
            return

        task_name = body.get("task_name")
        if not task_name:
            self._send_json(400, {"error": "missing task_name"})
            return

        batch_name = body.get("batch_name")
        state = self.tracker.get_task(task_name, batch_name=batch_name)
        if state is None:
            self._send_json(404, {"error": f"task {task_name} not registered (resume requires existing state)"})
            return

        with state.lock:
            if state.start_time is None:
                # A restart or a failed register can lose state, and recording now as
                # start_time would be inaccurate, so reject and tell the caller to use the fresh path.
                self._send_json(409, {
                    "error": "task timer was never started; call /start_timer for the fresh path instead of /resume_timer",
                    "task_name": task_name,
                })
                return
            # Clear any unpaired pause state from the previous round
            if state.active_evals != 0:
                logger.warning(
                    "[%s] resume_timer: leftover active_evals=%d, forcing to zero",
                    task_name, state.active_evals,
                )
                state.active_evals = 0
            if state.pause_start is not None:
                state.total_paused += time.time() - state.pause_start
                state.pause_start = None
            # Allow a new consecutive-failure count during the resume run
            state.consecutive_failures = 0
            state.should_skip = False
            elapsed = state.start_time and (time.time() - state.start_time - state.total_paused)

        logger.info(
            "[%s] resume_timer: resume confirmed, start_time=%s elapsed=%.1fs total_paused=%.1fs",
            task_name, state.start_time, elapsed or 0, state.total_paused,
        )
        self._send_json(200, {
            "status": "resumed",
            "task_name": task_name,
            "start_time": state.start_time,
            "total_paused": state.total_paused,
        })

    def _handle_pause_timer(self):
        """Handle POST /pause_timer — solve.py calls this after the container exits.

        Counts the current wall-clock into the pause (time when the task is not
        being worked on should not count toward agent solve time), just like the
        pause_timer used during evaluation. On the next resume, /resume_timer
        adds this duration into total_paused.

        Decoupled from the evaluate-internal pause_timer: only valid when
        active_evals==0, i.e. no evaluation is running on the server. If an
        evaluation is still running, this call is rejected to avoid breaking the
        evaluation-time pause state.
        """
        try:
            body = json.loads(self._read_body())
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"JSON failed to parse: {e}"})
            return

        task_name = body.get("task_name")
        if not task_name:
            self._send_json(400, {"error": "missing task_name"})
            return

        batch_name = body.get("batch_name")
        state = self.tracker.get_task(task_name, batch_name=batch_name)
        if state is None:
            self._send_json(404, {"error": f"task {task_name} not registered"})
            return

        with state.lock:
            if state.start_time is None:
                # Timer not started, pause is meaningless
                self._send_json(409, {
                    "error": "task timer not yet started; nothing to pause",
                    "task_name": task_name,
                })
                return
            if state.active_evals > 0:
                # Already paused while evaluation is in progress; do not interrupt again
                self._send_json(409, {
                    "error": "evaluation in progress, already paused",
                    "task_name": task_name,
                    "active_evals": state.active_evals,
                })
                return
            if state.pause_start is not None:
                # Already paused (e.g. a previous pause without a matching resume), return idempotently
                self._send_json(200, {
                    "status": "already_paused",
                    "task_name": task_name,
                    "pause_start": state.pause_start,
                    "total_paused": state.total_paused,
                })
                return
            state.pause_start = time.time()
            elapsed = time.time() - state.start_time - state.total_paused

        logger.info(
            "[%s] pause_timer: timer paused (container exit), elapsed_active=%.1fs total_paused=%.1fs",
            task_name, elapsed, state.total_paused,
        )
        self._send_json(200, {
            "status": "paused",
            "task_name": task_name,
            "pause_start": state.pause_start,
            "total_paused": state.total_paused,
        })


# ---------------------------------------------------------------------------
# Server startup
# ---------------------------------------------------------------------------

def create_server(
    host: str = "0.0.0.0",
    port: int = 8321,
    tracker: Optional[ScoreTracker] = None,
) -> ThreadingHTTPServer:
    """Create and return a multithreaded HTTP server instance (not started)."""
    if tracker is None:
        tracker = ScoreTracker()

    # Inject the tracker via a closure
    handler_class = type(
        "BoundEvalHandler",
        (EvalRequestHandler,),
        {"tracker": tracker},
    )

    server = ThreadingHTTPServer((host, port), handler_class)
    logger.info("Evaluation Service ready: http://%s:%d", host, port)
    return server


def start_server_background(
    host: str = "0.0.0.0",
    port: int = 8321,
    tracker: Optional[ScoreTracker] = None,
) -> Tuple[ThreadingHTTPServer, threading.Thread]:
    """Start the Evaluation Service in a background thread (multithreaded for concurrent requests)."""
    server = create_server(host, port, tracker)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Evaluation Service started in the background: http://%s:%d", host, port)
    return server, thread


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NatureBench Evaluation Service")
    parser.add_argument("--host", default="0.0.0.0", help="listen address")
    parser.add_argument("--port", type=int, default=8321, help="listen port")
    parser.add_argument(
        "--data-dir", default=None,
        help="task package root directory (containing per-task subdirectories). Optional: if omitted, tasks are registered only via POST /register",
    )
    parser.add_argument(
        "--tasks", nargs="*",
        help="list of task names to register (default: register all subdirectories under data-dir)",
    )
    parser.add_argument(
        "--timeout", type=int, default=3600,
        help="default task timeout (seconds), default 3600",
    )
    args = parser.parse_args()

    tracker = ScoreTracker()

    if args.data_dir:
        data_dir = Path(args.data_dir)
        if args.tasks:
            task_names = args.tasks
        else:
            task_names = [d.name for d in data_dir.iterdir() if d.is_dir()]

        for name in task_names:
            task_path = data_dir / name
            if task_path.exists():
                tbl, issues = tracker.register_task(name, task_path, timeout=args.timeout)
                for msg in issues:
                    logger.warning("[%s] METADATA: %s", name, msg)
                if tbl:
                    logger.info("task registered: %s (instances=%d)", name, len(tbl))
                else:
                    logger.error("[%s] metadata unavailable, not applied", name)
    else:
        logger.info("--data-dir not specified, waiting for tasks to be registered via POST /register")

    server = create_server(args.host, args.port, tracker)
    logger.info("Starting Evaluation Service, press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()
