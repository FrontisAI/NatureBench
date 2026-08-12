"""Registry-aware orchestration for post-hoc validity judging."""

from __future__ import annotations

import json
import logging
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import agent.cli_adapters  # noqa: F401
from agent.adapter import REGISTRY
from judge_core.attempts import (
    build_user_prompt_with_context,
    collect_attempt_context,
    collect_source_paper_context,
    collect_task_context,
    missing_context_files,
)
from judge_core.clients import call_judge, resolve_judge_config
from judge_core.policy import (
    DEFAULT_ANTHROPIC_BASE_URL,
    MAX_BYTES_PER_SOURCE_FILE,
    MAX_SOURCE_FILES,
)
from judge_core.policy import DEFAULT_JUDGE_MODEL as _DEFAULT_JUDGE_MODEL
from judge_core.policy import MAX_LOG_EXCERPT_BYTES as _MAX_LOG_EXCERPT_BYTES
from judge_core.sources import clip_text_bytes, collect_source_files
from judge_core.trace import excerpt_agent_log

logger = logging.getLogger(__name__)

# Backward-compatible names exposed by the previous monolithic judge module.
MAX_BYTES_PER_PY_FILE: int = MAX_BYTES_PER_SOURCE_FILE
MAX_PY_FILES: int = MAX_SOURCE_FILES
MAX_LOG_EXCERPT_BYTES: int = _MAX_LOG_EXCERPT_BYTES
DEFAULT_JUDGE_MODEL: str = _DEFAULT_JUDGE_MODEL
DEFAULT_JUDGE_BASE_URL: str = DEFAULT_ANTHROPIC_BASE_URL
DEFAULT_JUDGE_API_KEY: str | None = None

Verdict = dict[str, Any]
TaskTarget = tuple[str, Path]


def _source_paper_trace_terms(
    source_paper_context: dict[str, str],
) -> tuple[str, ...]:
    """Return equal-priority title/DOI terms for overflow trace selection."""
    title = source_paper_context.get("title", "").strip()
    doi = source_paper_context.get("doi", "").strip()
    terms = [term for term in (title, doi) if term]
    if "/" in doi:
        doi_suffix = doi.split("/", 1)[1].strip()
        if doi_suffix:
            terms.append(doi_suffix)
    return tuple(terms)


def collect_judge_inputs(
    task_out_dir: Path,
    agent_name: str = "claude",
    task_name: str | None = None,
    trace_relevance_terms: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Collect source, attempt, and adapter-selected transcript evidence."""
    workspace_dir = task_out_dir / "workspace"
    resolved_task_name = task_name or task_out_dir.name
    attempt_context = collect_attempt_context(resolved_task_name, task_out_dir)

    adapter = REGISTRY.get(agent_name) if REGISTRY.has(agent_name) else None
    log_path = adapter.transcript_path(task_out_dir) if adapter else None
    if log_path is None:
        log_excerpt = ""
        log_source = "none"
    else:
        assert adapter is not None
        custom_excerpt = adapter.excerpt_transcript(
            log_path,
            max_bytes=MAX_LOG_EXCERPT_BYTES,
            focus_start=attempt_context.get("focus_start"),
            focus_end=attempt_context.get("focus_end"),
        )
        log_excerpt = (
            excerpt_agent_log(
                log_path,
                max_bytes=MAX_LOG_EXCERPT_BYTES,
                focus_start=attempt_context.get("focus_start"),
                focus_end=attempt_context.get("focus_end"),
                relevance_terms=trace_relevance_terms,
            )
            if custom_excerpt is None
            else custom_excerpt
        )
        log_source = "stream" if log_path.name == f"{agent_name}.jsonl" else "state"
    log_excerpt = clip_text_bytes(log_excerpt, MAX_LOG_EXCERPT_BYTES)

    return {
        "code_files": collect_source_files(workspace_dir),
        "attempt_context": attempt_context,
        "agent_log_excerpt": log_excerpt,
        "log_source": log_source,
        "log_path": str(log_path) if log_path else None,
    }


def collect_judge_inputs_with_context(
    task_out_dir: Path,
    task_problem_dir: Path,
    agent_name: str = "claude",
    task_name: str | None = None,
) -> dict[str, Any]:
    """Collect task documentation together with source and transcript evidence."""
    resolved_task_name = task_name or task_out_dir.name
    source_paper_context = collect_source_paper_context(resolved_task_name)
    inputs = collect_judge_inputs(
        task_out_dir,
        agent_name=agent_name,
        task_name=task_name,
        trace_relevance_terms=_source_paper_trace_terms(source_paper_context),
    )
    inputs["source_paper_context"] = source_paper_context
    inputs["task_context"] = collect_task_context(task_problem_dir)
    return inputs


def _extract_json(text: str) -> dict[str, Any] | None:
    """Parse the first complete JSON object from judge output."""
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed

    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for index in range(start, len(text)):
        character = text[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                try:
                    candidate = json.loads(text[start : index + 1])
                except json.JSONDecodeError:
                    return None
                return candidate if isinstance(candidate, dict) else None
    return None


def judge_task(
    task_name: str,
    task_out_dir: Path,
    agent_name: str = "claude",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    task_problem_dir: Path | None = None,
) -> Verdict:
    """Judge one task and return a strict verdict or a task-level error."""
    _, resolved_model, resolved_base_url, resolved_api_key = resolve_judge_config(
        model,
        base_url,
        api_key,
    )
    if task_problem_dir is None:
        return {
            "is_valid": None,
            "reason": "judge_error: task problem directory is required",
            "model": resolved_model,
        }

    inputs = collect_judge_inputs_with_context(
        task_out_dir,
        task_problem_dir,
        agent_name=agent_name,
        task_name=task_name,
    )
    missing_context = missing_context_files(inputs)
    if missing_context:
        return {
            "is_valid": None,
            "reason": (
                "judge_error: missing or unreadable task context: "
                + ", ".join(missing_context)
            ),
            "model": resolved_model,
        }
    if inputs.get("attempt_context", {}).get("metadata_available", True) is False:
        return {
            "is_valid": None,
            "reason": "judge_error: final score attempt metadata unavailable",
            "model": resolved_model,
        }
    if not inputs["code_files"] and not inputs["agent_log_excerpt"]:
        return {
            "is_valid": None,
            "reason": "judge_error: no code files or log excerpt available",
            "model": resolved_model,
        }

    user_prompt = build_user_prompt_with_context(inputs)
    ok, text = call_judge(
        user_prompt,
        model=resolved_model,
        base_url=resolved_base_url,
        api_key=resolved_api_key,
    )
    if not ok:
        logger.warning("[%s] judge API failed: %s", task_name, text[:200])
        return {
            "is_valid": None,
            "reason": f"judge_error: {text[:300]}",
            "model": resolved_model,
        }

    parsed = _extract_json(text)
    if parsed is None or "is_valid" not in parsed:
        logger.warning(
            "[%s] judge returned unparseable output: %s",
            task_name,
            text[:300],
        )
        return {
            "is_valid": None,
            "reason": f"judge_error: unparseable output: {text[:300]}",
            "model": resolved_model,
            "raw": text[:1000],
        }

    is_valid = parsed.get("is_valid")
    reason = parsed.get("reason")
    if type(is_valid) is not bool or not isinstance(reason, str) or not reason.strip():
        logger.warning(
            "[%s] judge returned invalid verdict schema: %s",
            task_name,
            text[:300],
        )
        return {
            "is_valid": None,
            "reason": "judge_error: invalid verdict schema",
            "model": resolved_model,
            "raw": text[:1000],
        }
    return {
        "is_valid": is_valid,
        "reason": reason.strip()[:1000],
        "model": resolved_model,
    }


def _write_judge_verdict(
    task_name: str,
    task_out_dir: Path,
    verdict: Verdict,
) -> None:
    """Persist one verdict without interrupting other judge tasks."""
    try:
        (task_out_dir / "judge_verdict.json").write_text(
            json.dumps(verdict, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as error:
        logger.warning(
            "[%s] failed to write judge_verdict.json: %s",
            task_name,
            error,
        )


def run_judges(
    tasks: list[TaskTarget],
    agent_name: str = "claude",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    max_workers: int = 4,
    data_dir: Path | None = None,
) -> dict[str, Verdict]:
    """Judge tasks concurrently and persist a verdict for every target."""
    results: dict[str, Verdict] = {}
    if not tasks:
        return results

    provider, resolved_model, resolved_base_url, resolved_api_key = (
        resolve_judge_config(model, base_url, api_key)
    )
    if not resolved_api_key:
        logger.warning(
            "Judge skipped: no %s API key configured; set a provider-specific "
            "judge key or JUDGE_API_KEY",
            provider,
        )
        for task_name, task_out_dir in tasks:
            verdict = {
                "is_valid": None,
                "reason": "judge_error: no API key configured",
                "model": resolved_model,
            }
            results[task_name] = verdict
            _write_judge_verdict(task_name, task_out_dir, verdict)
        return results

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map: dict[Future[Verdict], TaskTarget] = {}
        for task_name, task_out_dir in tasks:
            task_problem_dir = (
                data_dir / task_name / "problem" if data_dir is not None else None
            )
            future = executor.submit(
                judge_task,
                task_name,
                task_out_dir,
                agent_name,
                resolved_model,
                resolved_base_url,
                resolved_api_key,
                task_problem_dir,
            )
            future_map[future] = (task_name, task_out_dir)

        for future in as_completed(future_map):
            task_name, task_out_dir = future_map[future]
            try:
                verdict = future.result()
            except Exception as error:  # noqa: BLE001 - isolate any task failure
                verdict = {
                    "is_valid": None,
                    "reason": (
                        "judge_error: unexpected exception: "
                        + type(error).__name__
                    ),
                    "model": resolved_model,
                }
            results[task_name] = verdict
            _write_judge_verdict(task_name, task_out_dir, verdict)
            tag = (
                "valid"
                if verdict.get("is_valid") is True
                else "invalid"
                if verdict.get("is_valid") is False
                else "error"
            )
            reason = verdict.get("reason")
            reason_text = reason if isinstance(reason, str) else ""
            logger.info(
                "[%s] judge=%s: %s",
                task_name,
                tag,
                reason_text[:200],
            )
    return results


def apply_verdicts_to_results(
    results: list[dict[str, Any]],
    verdicts: dict[str, Verdict],
) -> None:
    """Attach verdicts and discard scores only for explicit invalidity."""
    for result in results:
        task_name = result.get("task_name")
        verdict = verdicts.get(task_name) if isinstance(task_name, str) else None
        best = result.get("best_aggregate_improvement")
        if verdict is None:
            result["judge"] = None
            result["effective_improvement"] = best
            continue
        result["judge"] = verdict
        if verdict.get("is_valid") is False:
            result["effective_improvement"] = None
        else:
            result["effective_improvement"] = best


def judge_task_v2(
    task_name: str,
    task_out_dir: Path,
    task_problem_dir: Path,
    agent_name: str = "claude",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> Verdict:
    """Run ``judge_task`` with the previous README-aware signature."""
    return judge_task(
        task_name,
        task_out_dir,
        agent_name=agent_name,
        model=model,
        base_url=base_url,
        api_key=api_key,
        task_problem_dir=task_problem_dir,
    )


def run_judges_v2(
    tasks: list[TaskTarget],
    data_dir: Path,
    agent_name: str = "claude",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    max_workers: int = 4,
) -> dict[str, Verdict]:
    """Run ``run_judges`` with the previous README-aware signature."""
    return run_judges(
        tasks,
        agent_name=agent_name,
        model=model,
        base_url=base_url,
        api_key=api_key,
        max_workers=max_workers,
        data_dir=data_dir,
    )


__all__ = [
    "DEFAULT_JUDGE_API_KEY",
    "DEFAULT_JUDGE_BASE_URL",
    "MAX_BYTES_PER_PY_FILE",
    "MAX_PY_FILES",
    "apply_verdicts_to_results",
    "collect_judge_inputs",
    "collect_judge_inputs_with_context",
    "judge_task",
    "judge_task_v2",
    "run_judges",
    "run_judges_v2",
]
