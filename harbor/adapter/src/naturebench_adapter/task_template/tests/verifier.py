from __future__ import annotations

import json
import math
import os
import shutil
import sys
from pathlib import Path
from typing import Any

JUDGE_TRACE_PATH = Path("/agent.jsonl")
JUDGE_AGENT_NAME = "agent"


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
            elif item.get("type") == "image":
                source = item.get("source")
                if isinstance(source, dict):
                    parts.append(
                        "[image media_type="
                        + str(source.get("media_type", ""))
                        + " path="
                        + str(source.get("path", ""))
                        + "]"
                    )
        return "\n".join(parts)
    return ""


def _claude_role(source: Any) -> str:
    return "assistant" if source == "agent" else str(source or "assistant")


def _trajectory_lines(
    trajectory: dict[str, Any],
    *,
    subagent_label: str | None = None,
) -> list[str]:
    lines: list[str] = []
    if subagent_label is not None:
        agent = trajectory.get("agent")
        header = {
            "trajectory_id": trajectory.get("trajectory_id"),
            "session_id": trajectory.get("session_id"),
            "agent": agent if isinstance(agent, dict) else {},
        }
        lines.append(
            json.dumps(
                {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": f"[atif subagent {subagent_label}] "
                                + json.dumps(header, ensure_ascii=False),
                            }
                        ],
                    }
                },
                ensure_ascii=False,
            )
        )
    for step in trajectory.get("steps", []):
        if not isinstance(step, dict):
            continue
        content: list[dict[str, Any]] = []
        message = _text(step.get("message"))
        reasoning = step.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning:
            content.append({"type": "text", "text": f"[reasoning] {reasoning}"})
        if message:
            content.append({"type": "text", "text": message})
        for call in step.get("tool_calls") or []:
            if isinstance(call, dict):
                call_id = call.get("tool_call_id")
                if call_id:
                    content.append(
                        {"type": "text", "text": f"[atif tool_call_id={call_id}]"}
                    )
                content.append(
                    {
                        "type": "tool_use",
                        "name": call.get("function_name", ""),
                        "input": call.get("arguments", {}),
                    }
                )
        observation = step.get("observation") or {}
        if isinstance(observation, dict):
            for result in observation.get("results") or []:
                if isinstance(result, dict):
                    observation_metadata = {
                        key: result[key]
                        for key in (
                            "source_call_id",
                            "subagent_trajectory_ref",
                            "extra",
                        )
                        if result.get(key) is not None
                    }
                    if observation_metadata:
                        content.append(
                            {
                                "type": "text",
                                "text": "[atif observation] "
                                + json.dumps(observation_metadata, ensure_ascii=False),
                            }
                        )
                    result_text = _text(result.get("content"))
                    if result_text:
                        content.append(
                            {"type": "tool_result", "content": result_text}
                        )
        if not content:
            continue
        lines.append(
            json.dumps(
                {
                    "timestamp": step.get("timestamp"),
                    "message": {
                        "role": _claude_role(step.get("source")),
                        "content": content,
                    },
                },
                ensure_ascii=False,
            )
        )
    for index, subagent in enumerate(trajectory.get("subagent_trajectories") or []):
        if not isinstance(subagent, dict):
            continue
        label = str(subagent.get("trajectory_id") or f"embedded-{index + 1}")
        lines.extend(_trajectory_lines(subagent, subagent_label=label))
    return lines


def atif_to_naturebench_jsonl(source: Path, target: Path) -> None:
    trajectory = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(trajectory, dict):
        raise ValueError(f"ATIF trajectory must be an object: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = _trajectory_lines(trajectory)
    target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def reward_from_verdict(
    best_aggregate_improvement: float | None,
    verdict: dict[str, Any] | None,
) -> float:
    if best_aggregate_improvement is None:
        return -1.0
    if verdict is not None and verdict.get("is_valid") is False:
        return -1.0
    return float(best_aggregate_improvement)



def summary_from_best(
    best: dict[str, Any] | None,
    verdict: dict[str, Any],
) -> dict[str, Any]:
    best_attempt: int | None = None
    best_aggregate_improvement: float | None = None
    if best is not None:
        score = best.get("best_aggregate_improvement")
        if (
            isinstance(score, (int, float))
            and not isinstance(score, bool)
            and math.isfinite(score)
        ):
            best_aggregate_improvement = float(score)
            attempt = best.get("best_attempt")
            if isinstance(attempt, int) and not isinstance(attempt, bool):
                best_attempt = attempt
    effective_improvement = (
        None
        if best_aggregate_improvement is None or verdict.get("is_valid") is False
        else best_aggregate_improvement
    )
    return {
        "best_attempt": best_attempt,
        "best_aggregate_improvement": best_aggregate_improvement,
        "judge": verdict,
        "effective_improvement": effective_improvement,
    }

def task_id_from_source_paper_index(path: Path) -> str:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"invalid source-paper record at {path}:{line_number}"
            ) from error
        if isinstance(record, dict):
            records.append(record)
    if len(records) != 1:
        raise ValueError(
            f"expected exactly one source-paper record in {path}, found {len(records)}"
        )
    task_id = records[0].get("case_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError(f"source-paper record in {path} has no valid case_id")
    return task_id.strip()


def _write_outputs(
    reward: float,
    verdict: dict[str, Any],
    best: dict[str, Any] | None,
    *,
    log_dir: Path = Path("/logs/verifier"),
) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (log_dir / "reward.json").write_text(
        json.dumps({"reward": reward}, indent=2) + "\n", encoding="utf-8"
    )
    (log_dir / "judge_verdict.json").write_text(
        json.dumps(verdict, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (log_dir / "summary.json").write_text(
        json.dumps(
            summary_from_best(best, verdict),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def run_verifier() -> float:
    best_path = Path("/state/best_score.json")
    if not best_path.is_file():
        verdict = {"is_valid": None, "reason": "infrastructure_error: best_score.json missing"}
        _write_outputs(-1.0, verdict, None)
        raise RuntimeError(verdict["reason"])
    best = json.loads(best_path.read_text(encoding="utf-8"))
    if best.get("finalized") is not True:
        verdict = {"is_valid": None, "reason": "infrastructure_error: best_score.json is not finalized"}
        _write_outputs(-1.0, verdict, None)
        raise RuntimeError(verdict["reason"])
    score = best.get("best_aggregate_improvement")
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score):
        verdict = {
            "is_valid": None,
            "reason": "judge_skipped: no valid evaluation score",
            "model": os.environ.get("JUDGE_MODEL", "gpt-5.5"),
        }
        _write_outputs(-1.0, verdict, best)
        return -1.0

    task_id = task_id_from_source_paper_index(
        Path("/tests/judge_source_papers.jsonl")
    )
    trajectory = Path("/logs/agent/trajectory.json")
    submissions = Path("/state/submissions.jsonl")
    if not trajectory.is_file():
        verdict = {
            "is_valid": None,
            "reason": "judge_error: Harbor ATIF trajectory artifact is missing",
            "model": os.environ.get("JUDGE_MODEL", "gpt-5.5"),
        }
    elif not submissions.is_file():
        verdict = {
            "is_valid": None,
            "reason": "judge_error: submissions.jsonl artifact is missing",
            "model": os.environ.get("JUDGE_MODEL", "gpt-5.5"),
        }
    else:
        atif_to_naturebench_jsonl(trajectory, JUDGE_TRACE_PATH)
        shutil.copyfile(submissions, "/submissions.jsonl")
        try:
            import judge_readme

            verdict = judge_readme.judge_task(
                task_id,
                Path("/"),
                agent_name=JUDGE_AGENT_NAME,
                task_problem_dir=Path("/tests/context"),
            )
        except Exception as error:
            verdict = {
                "is_valid": None,
                "reason": f"judge_error: unexpected exception: {error}",
                "model": os.environ.get("JUDGE_MODEL", "gpt-5.5"),
            }
    reward = reward_from_verdict(float(score), verdict)
    _write_outputs(reward, verdict, best)
    return reward


def main() -> None:
    reward = run_verifier()
    print(f"NatureBench reward: {reward}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise
