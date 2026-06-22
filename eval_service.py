"""eval_service.py — 宿主机 Evaluation Service (HTTP)

为解题容器中的 Solver Agent 提供评测接口。Agent 在容器内生成结果文件后，
通过 HTTP 调用本服务获取得分，并可多次迭代优化。

端点:
    POST /evaluate      — 提交预测结果，返回得分
    POST /register      — 动态注册任务
    POST /start_timer   — 通知某任务开始计时（solve.py 在启动 agent 前调用）
    GET  /best_score    — 查询某任务当前最高分
    GET  /time_remaining — 查询剩余时间
    GET  /health        — 健康检查
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
# 得分追踪
# ---------------------------------------------------------------------------

@dataclass
class SubmissionRecord:
    """单次提交记录"""
    attempt: int
    raw_scores: Dict[str, Any]                     # evaluator 返回的完整嵌套 dict
    per_instance_improvement: Dict[str, float]     # {instance: improvement}
    aggregate_improvement: Optional[float]         # mean of per_instance, 若全缺则 None


@dataclass
class TaskState:
    """单个任务的评测状态"""
    task_name: str
    data_dir: Path                          # 任务包根目录
    out_dir: Optional[Path] = None          # 宿主机输出目录（落 submissions.jsonl 用）
    primary_table: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # per-instance primary 信息
    submissions: List[SubmissionRecord] = field(default_factory=list)
    best_attempt: Optional[int] = None
    best_aggregate_improvement: Optional[float] = None
    start_time: Optional[float] = None      # 任务开始时间 (time.time())
    timeout: Optional[int] = None           # 任务超时秒数
    lock: threading.Lock = field(default_factory=threading.Lock)
    # ---- 评测期间暂停计时 ----
    total_paused: float = 0.0               # 累计暂停秒数
    active_evals: int = 0                   # 当前并发评测数（>0 表示暂停中）
    pause_start: Optional[float] = None     # 本次暂停开始时刻
    # ---- 连续失败自动跳过 ----
    consecutive_failures: int = 0           # 连续评测异常次数
    should_skip: bool = False               # 连续失败 ≥ 阈值，通知 solve.py 终止容器

    def pause_timer(self) -> None:
        """评测开始时调用。首个并发评测会记录暂停起点。"""
        with self.lock:
            self.active_evals += 1
            if self.active_evals == 1:
                self.pause_start = time.time()

    def resume_timer(self) -> None:
        """评测结束时调用。最后一个并发评测结束后累加暂停时长。"""
        with self.lock:
            self.active_evals -= 1
            if self.active_evals == 0 and self.pause_start is not None:
                self.total_paused += time.time() - self.pause_start
                self.pause_start = None

    def get_effective_elapsed(self) -> float:
        """返回扣除暂停后的有效经过时间。"""
        with self.lock:
            if self.start_time is None:
                return 0.0
            raw = time.time() - self.start_time
            paused = self.total_paused
            if self.pause_start is not None:
                paused += time.time() - self.pause_start
            return max(0.0, raw - paused)

    def record(self, rec: SubmissionRecord) -> None:
        """记录一次 attempt 并按 max(aggregate_improvement) 更新 best。"""
        with self.lock:
            self.submissions.append(rec)
            if rec.aggregate_improvement is not None:
                if (self.best_aggregate_improvement is None
                        or rec.aggregate_improvement > self.best_aggregate_improvement):
                    self.best_aggregate_improvement = rec.aggregate_improvement
                    self.best_attempt = rec.attempt


class ScoreTracker:
    """全局得分追踪器，线程安全。

    State key 是 (task_name, batch_name) 元组，让不同 batch/agent 跑同名 task
    时互不污染。batch_name 缺省值为 "default"。
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
        """注册任务。

        Args:
          batch_name: 隔离命名空间。同 task_name 不同 batch 互不污染。
          force: True → 重置 start_time/timeout 并清空 submissions（强制 rerun）；
                 False → 已存在则保留 submissions/best_score；如果 start_time
                         尚未设置（首次启动）才允许重置 timer 状态，否则保持
                         既有计时上下文不动（resume 友好）。
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
# 评测核心逻辑
# ---------------------------------------------------------------------------


def _bn_from_query(parsed) -> Optional[str]:
    """Extract batch_name from URL query string, if present."""
    from urllib.parse import parse_qs as _pq
    val = _pq(parsed.query).get("batch_name", [None])[0]
    return val if val else None



# ---------------------------------------------------------------------------
# AutoSOTA-style 归一化打分
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
    """从 sota_score 字段提取按方向最强的数值。

    sota_score 可能是 list / 单个 dict / scalar / 非数字字符串。
    每个候选经 _parse_one_score 解析（支持 ±、(…)、~、<、ranges 等变体）；
    higher_is_better=True 取最大；False 取最小。
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
    """从 metadata.json 提取每个 performance entry 的 primary metric 信息。

    Returns:
        (table, issues):
          table = {instance_name: {"metric", "higher_is_better", "sota"}}
          issues = 文字形式的具体问题清单（注册时按 warning 打）
        缺 sota_score、缺 is_primary metric、或 sota 无法解析的 instance 不进表。
    """
    issues: List[str] = []
    if not metadata_path.exists():
        issues.append(f"metadata.json 不存在: {metadata_path}")
        return ({}, issues)
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        issues.append(f"metadata.json 解析失败: {e}")
        return ({}, issues)
    table: Dict[str, Dict[str, Any]] = {}
    entries = metadata.get("performance_entries", [])
    if not entries:
        issues.append("metadata.performance_entries 为空")
        return ({}, issues)
    for entry in entries:
        instance = entry.get("dataset_name") or entry.get("instance_name")
        if not instance:
            issues.append("performance_entries 中有 entry 缺 dataset_name")
            continue
        primary = next(
            (m for m in entry.get("metrics", []) if m.get("is_primary")),
            None,
        )
        if primary is None:
            issues.append(f"instance={instance}: 没有 is_primary metric, 已跳过")
            continue
        metric_name = primary.get("name")
        if not metric_name:
            issues.append(f"instance={instance}: primary metric 缺 name, 已跳过")
            continue
        higher_is_better = primary.get("metric_direction") == "higher_is_better"
        sota = _best_sota(primary.get("sota_score"), higher_is_better)
        if sota is None:
            issues.append(
                f"instance={instance}, metric={metric_name}: 缺或无法解析 sota_score, 已跳过"
            )
            continue
        if sota == 0:
            issues.append(
                f"instance={instance}, metric={metric_name}: sota_score=0 无法归一化, 已跳过"
            )
            continue
        table[instance] = {
            "metric": metric_name,
            "higher_is_better": higher_is_better,
            "sota": sota,
        }
    return (table, issues)


def _find_metric_value(scores: Any, target_metric: str) -> Optional[float]:
    """递归在嵌套 dict 中查找匹配 target_metric 名字的数值。

    名字匹配做模糊化（去 _ - 空格 + 小写）。
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
    """按 AutoSOTA-style 归一化计算 per-instance improvement 与聚合分数。

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
    """通过 subprocess 隔离运行任务包的 evaluator.py，避免共享 os.environ 造成的 race condition。

    Args:
        task_data_dir: 任务包根目录（包含 evaluation/evaluator.py）
        output_dir: Agent 输出目录（evaluator 通过 OUTPUT_DIR 环境变量读取）

    Returns:
        evaluator 返回的 results dict
    """
    import subprocess as _subp

    evaluator_script = task_data_dir / "evaluation" / "evaluator.py"
    if not evaluator_script.exists():
        raise FileNotFoundError(f"evaluator.py 未找到: {evaluator_script}")

    wrapper = Path(__file__).parent / "_evaluator_runner.py"
    if not wrapper.exists():
        raise FileNotFoundError(f"_evaluator_runner.py 未找到: {wrapper}")

    # 子进程独立的环境，避免线程间 os.environ["OUTPUT_DIR"] 互相覆盖
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
        # 暴露 stderr 末尾以便调试
        raise RuntimeError(
            f"evaluator subprocess failed (exit {proc.returncode}): "
            f"{(proc.stderr or '')[-1500:]}"
        )

    # 从 stdout 末尾找 marker 后的 JSON
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
# HTTP 请求处理
# ---------------------------------------------------------------------------

class EvalRequestHandler(BaseHTTPRequestHandler):
    """处理评测 HTTP 请求"""

    tracker: ScoreTracker  # 由 server 注入

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
                self._send_json(400, {"error": "缺少 task_name 参数"})
                return
            state = self.tracker.get_task(task_name, batch_name=_bn_from_query(parsed))
            if state is None:
                self._send_json(404, {"error": f"任务 {task_name} 未注册"})
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
                self._send_json(400, {"error": "缺少 task_name 参数"})
                return
            state = self.tracker.get_task(task_name, batch_name=_bn_from_query(parsed))
            if state is None:
                self._send_json(404, {"error": f"任务 {task_name} 未注册"})
                return
            elapsed = state.get_effective_elapsed()
            remaining = max(0, state.timeout - elapsed) if state.timeout else None
            # 计算当前累计暂停时间（含正在进行的暂停）
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

        self._send_json(404, {"error": "未知端点"})

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

        self._send_json(404, {"error": "未知端点"})

    def _handle_evaluate(self):
        """处理 POST /evaluate

        请求体 JSON:
        {
            "task_name": "s42256-020-0209-y",
            "output_dir": "/workspace/output"   // 容器内的输出目录路径
        }

        由于 output_dir 是容器内路径，我们需要通过挂载映射来访问。
        实际上，我们让 Agent 把结果文件内容直接传过来更简单。

        支持两种模式:
        模式 A — 传文件路径（需要宿主机能访问）:
            {"task_name": "...", "output_dir": "/host/path/to/output"}
        模式 B — 传结果数据（推荐，容器内使用）:
            {"task_name": "...", "predictions": {"instance_name": {"sample_id": label, ...}}}
        """
        try:
            body = json.loads(self._read_body())
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"JSON 解析失败: {e}"})
            return

        task_name = body.get("task_name")
        if not task_name:
            self._send_json(400, {"error": "缺少 task_name"})
            return

        state = self.tracker.get_task(task_name, batch_name=body.get("batch_name") if body else None)
        if state is None:
            self._send_json(404, {"error": f"任务 {task_name} 未注册"})
            return

        # 暂停该任务的倒计时（评测期间不计入 agent 解题时间）
        state.pause_timer()
        try:
            output_dir_str = body.get("output_dir")
            if not output_dir_str:
                self._send_json(400, {"error": "缺少 output_dir"})
                return

            output_dir = Path(output_dir_str)
            if not output_dir.exists():
                self._send_json(400, {"error": f"output_dir 不存在: {output_dir}"})
                return

            # 调用 evaluator
            results = run_evaluator(state.data_dir, output_dir)

            # AutoSOTA-style 归一化：per-instance improvement + 聚合
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

            # ---- 持久化到 submissions.jsonl ----
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
                    logger.warning("[%s] 写 submissions.jsonl 失败: %s", task_name, e)

            # ---- 连续失败追踪 ----
            if aggregate_improvement is None:
                state.consecutive_failures += 1
                logger.warning(
                    "[%s] aggregate_improvement=None (consecutive_failures=%d)",
                    task_name, state.consecutive_failures,
                )
                if state.consecutive_failures >= CONSEC_FAIL_SKIP_THRESHOLD:
                    state.should_skip = True
                    logger.warning(
                        "[%s] 连续 %d 次评测无有效分数，标记为 should_skip",
                        task_name, state.consecutive_failures,
                    )
            else:
                state.consecutive_failures = 0

            logger.info(
                "[%s] 评测完成 (attempt=%d): aggregate_improvement=%s, best=%s",
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
            logger.error("[%s] 评测失败: %s", task_name, traceback.format_exc())
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
                logger.warning("[%s] state.record(failure) 失败: %s", task_name, _e_rec)
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
                    logger.warning("[%s] 写 submissions.jsonl (failure) 失败: %s", task_name, _e_io)
            # ---- 连续失败追踪（异常也算） ----
            state.consecutive_failures += 1
            if state.consecutive_failures >= CONSEC_FAIL_SKIP_THRESHOLD:
                state.should_skip = True
                logger.warning(
                    "[%s] 连续 %d 次评测异常，标记为 should_skip",
                    task_name, state.consecutive_failures,
                )
            self._send_json(500, {
                "error": f"评测失败: {e}",
                "traceback": traceback.format_exc(),
            })
        finally:
            # 恢复该任务的倒计时（无论评测成功或失败）
            state.resume_timer()

    def _handle_register(self):
        """处理 POST /register — 动态注册任务

        请求体 JSON:
        {
            "task_name": "s42256-xxx",
            "data_dir": "/full/path/to/task",
            "timeout": 3600           // 可选
        }
        """
        try:
            body = json.loads(self._read_body())
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"JSON 解析失败: {e}"})
            return

        task_name = body.get("task_name")
        if not task_name:
            self._send_json(400, {"error": "缺少 task_name"})
            return

        data_dir_str = body.get("data_dir")
        if not data_dir_str:
            self._send_json(400, {"error": "缺少 data_dir"})
            return

        data_dir = Path(data_dir_str)
        if not data_dir.exists():
            self._send_json(400, {
                "error": f"data_dir 不存在: {data_dir_str}",
            })
            return

        timeout = body.get("timeout")
        out_dir_str = body.get("out_dir")
        out_dir = Path(out_dir_str) if out_dir_str else None
        if out_dir is not None:
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.warning("[%s] out_dir 创建失败 (%s): %s", task_name, out_dir, e)
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
                "[%s] METADATA: 没有可用的 instance（缺 sota_score / 缺 primary metric / 全空），"
                "拒绝注册。修复 metadata.json 后重跑。", task_name,
            )
            self._send_json(422, {
                "status": "incomplete_metadata",
                "task_name": task_name,
                "issues": issues,
            })
            return
        logger.info("[%s] 动态注册任务: data_dir=%s, timeout=%s, out_dir=%s, instances=%d",
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
        """处理 POST /start_timer — solve.py 通知某任务开始计时

        请求体 JSON:
        {
            "task_name": "s42256-xxx"
        }
        """
        try:
            body = json.loads(self._read_body())
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"JSON 解析失败: {e}"})
            return

        task_name = body.get("task_name")
        if not task_name:
            self._send_json(400, {"error": "缺少 task_name"})
            return

        batch_name = body.get("batch_name")
        state = self.tracker.get_task(task_name, batch_name=batch_name)
        if state is None:
            self._send_json(404, {"error": f"任务 {task_name} 未注册"})
            return

        with state.lock:
            if state.start_time is not None:
                # 已经启动过，忽略重复调用（防止 Agent 重置计时器）
                self._send_json(200, {
                    "status": "already_started",
                    "task_name": task_name,
                    "start_time": state.start_time,
                })
                return
            state.start_time = time.time()

        logger.info("[%s] 计时器已启动", task_name)
        self._send_json(200, {
            "status": "ok",
            "task_name": task_name,
            "start_time": state.start_time,
        })

    def _handle_resume_timer(self):
        """处理 POST /resume_timer — solve.py 在 resume 跑前调用。

        语义与 /start_timer 互补：要求该任务的计时器**已经**启动过，
        本调用仅确认服务端 task state 仍然存在并清理上次运行可能残留的
        active_evals/pause_start，**绝不重置** start_time / total_paused
        / submissions / best_score（这些都要在 resume 中续接）。
        """
        try:
            body = json.loads(self._read_body())
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"JSON 解析失败: {e}"})
            return

        task_name = body.get("task_name")
        if not task_name:
            self._send_json(400, {"error": "缺少 task_name"})
            return

        batch_name = body.get("batch_name")
        state = self.tracker.get_task(task_name, batch_name=batch_name)
        if state is None:
            self._send_json(404, {"error": f"任务 {task_name} 未注册（resume 需要既有状态）"})
            return

        with state.lock:
            if state.start_time is None:
                # 服务重启或 register 失败导致状态丢失：把现在记为 start_time
                # 是不准确的，所以拒绝并提示调用方走 fresh 路径。
                self._send_json(409, {
                    "error": "任务计时器从未启动；请先调用 /start_timer 走 fresh 路径，而非 /resume_timer",
                    "task_name": task_name,
                })
                return
            # 清理上一轮可能未配对的暂停状态
            if state.active_evals != 0:
                logger.warning(
                    "[%s] resume_timer: 残留 active_evals=%d, 强制归零",
                    task_name, state.active_evals,
                )
                state.active_evals = 0
            if state.pause_start is not None:
                state.total_paused += time.time() - state.pause_start
                state.pause_start = None
            # 续跑期间允许新的连续失败计数
            state.consecutive_failures = 0
            state.should_skip = False
            elapsed = state.start_time and (time.time() - state.start_time - state.total_paused)

        logger.info(
            "[%s] resume_timer: 续跑确认，start_time=%s elapsed=%.1fs total_paused=%.1fs",
            task_name, state.start_time, elapsed or 0, state.total_paused,
        )
        self._send_json(200, {
            "status": "resumed",
            "task_name": task_name,
            "start_time": state.start_time,
            "total_paused": state.total_paused,
        })

    def _handle_pause_timer(self):
        """处理 POST /pause_timer — solve.py 在容器退出后调用。

        语义：把当前 wall-clock 计入暂停（task 不在工作的时段不应该计入
        agent 解题时间），就像评测期间的 pause_timer 一样。再次 resume 时
        通过 /resume_timer 把这段时长累加到 total_paused。

        与 evaluate-internal 的 pause_timer 解耦：只要 active_evals==0 时
        服务端没有正在跑的评测；如果尚有评测在跑，本调用会拒绝以避免
        破坏评测期间的暂停状态。
        """
        try:
            body = json.loads(self._read_body())
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"JSON 解析失败: {e}"})
            return

        task_name = body.get("task_name")
        if not task_name:
            self._send_json(400, {"error": "缺少 task_name"})
            return

        batch_name = body.get("batch_name")
        state = self.tracker.get_task(task_name, batch_name=batch_name)
        if state is None:
            self._send_json(404, {"error": f"任务 {task_name} 未注册"})
            return

        with state.lock:
            if state.start_time is None:
                # Timer 未启动，pause 没有意义
                self._send_json(409, {
                    "error": "任务计时器尚未启动；无需暂停",
                    "task_name": task_name,
                })
                return
            if state.active_evals > 0:
                # 评测进行中已经在 paused 状态，不要重复打断
                self._send_json(409, {
                    "error": "评测进行中，已经处于暂停状态",
                    "task_name": task_name,
                    "active_evals": state.active_evals,
                })
                return
            if state.pause_start is not None:
                # 已经在暂停中（比如上次 pause 没配对 resume），幂等返回
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
            "[%s] pause_timer: 暂停计时（容器退出），elapsed_active=%.1fs total_paused=%.1fs",
            task_name, elapsed, state.total_paused,
        )
        self._send_json(200, {
            "status": "paused",
            "task_name": task_name,
            "pause_start": state.pause_start,
            "total_paused": state.total_paused,
        })


# ---------------------------------------------------------------------------
# 服务启动
# ---------------------------------------------------------------------------

def create_server(
    host: str = "0.0.0.0",
    port: int = 8321,
    tracker: Optional[ScoreTracker] = None,
) -> ThreadingHTTPServer:
    """创建并返回多线程 HTTP 服务器实例（不启动）"""
    if tracker is None:
        tracker = ScoreTracker()

    # 通过闭包注入 tracker
    handler_class = type(
        "BoundEvalHandler",
        (EvalRequestHandler,),
        {"tracker": tracker},
    )

    server = ThreadingHTTPServer((host, port), handler_class)
    logger.info("Evaluation Service 准备就绪: http://%s:%d", host, port)
    return server


def start_server_background(
    host: str = "0.0.0.0",
    port: int = 8321,
    tracker: Optional[ScoreTracker] = None,
) -> Tuple[ThreadingHTTPServer, threading.Thread]:
    """在后台线程启动 Evaluation Service（多线程处理并发请求）"""
    server = create_server(host, port, tracker)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Evaluation Service 已在后台启动: http://%s:%d", host, port)
    return server, thread


# ---------------------------------------------------------------------------
# 独立运行入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NatureBench Evaluation Service")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8321, help="监听端口")
    parser.add_argument(
        "--data-dir", default=None,
        help="任务包根目录（包含各任务子目录）。可选：若省略则仅通过 POST /register 注册任务",
    )
    parser.add_argument(
        "--tasks", nargs="*",
        help="要注册的任务名列表（默认注册 data-dir 下所有子目录）",
    )
    parser.add_argument(
        "--timeout", type=int, default=3600,
        help="默认任务超时时间（秒），默认 3600",
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
                    logger.info("已注册任务: %s (instances=%d)", name, len(tbl))
                else:
                    logger.error("[%s] metadata 不可用，未生效", name)
    else:
        logger.info("未指定 --data-dir，等待通过 POST /register 注册任务")

    server = create_server(args.host, args.port, tracker)
    logger.info("启动 Evaluation Service，按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("正在关闭...")
        server.shutdown()
