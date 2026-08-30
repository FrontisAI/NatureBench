from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .control import control_request
from .evaluation import atomic_write_json


def get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=10) as response:
        value = json.loads(response.read())
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object from {url}")
    return value


def drain_and_finalize(
    state_path: Path = Path("/state/best_score.json"),
    base_url: str = "http://localhost:8000",
    poll_seconds: float = 2.0,
    max_connection_failures: int = 30,
) -> dict[str, Any]:
    failures = 0
    while True:
        try:
            timer = get_json(f"{base_url}/time_remaining")
            failures = 0
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            failures += 1
            if failures >= max_connection_failures:
                raise RuntimeError("evaluation service remained unreachable during drain")
            time.sleep(poll_seconds)
            continue
        if not timer.get("is_paused"):
            break
        time.sleep(poll_seconds)

    control_request({"action": "stop"})
    best = get_json(f"{base_url}/best_score")
    timer = get_json(f"{base_url}/time_remaining")
    final = {
        **best,
        "status": (
            "scored"
            if best.get("best_aggregate_improvement") is not None
            else "no_score"
        ),
        "finalized": True,
        "effective_elapsed_seconds": timer.get("elapsed_seconds"),
        "evaluation_paused_seconds": timer.get("total_paused_seconds"),
        "timeout_seconds": timer.get("timeout_seconds"),
        "remaining_seconds": timer.get("remaining_seconds"),
        "finalized_at": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
    }
    atomic_write_json(state_path, final)
    return final


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-path", type=Path, default=Path("/state/best_score.json"))
    args = parser.parse_args()
    print(json.dumps(drain_and_finalize(args.state_path), indent=2))


if __name__ == "__main__":
    main()
