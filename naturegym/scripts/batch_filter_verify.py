#!/usr/bin/env python3
"""
Batch runner for filter-verify with Claude Code.

Usage:
    python batch_filter_verify.py [-j N] <parent_folder>
    python batch_filter_verify.py [-j N] --single <folder>
    python batch_filter_verify.py [-j N] --start 11 --end 20 <parent_folder>

Example:
    python batch_filter_verify.py -j 4 dataset/papers
    python batch_filter_verify.py --single dataset/papers/paper_001
    python batch_filter_verify.py --start 11 --end 20 dataset/papers
"""

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Optional, Tuple

from batch_target_utils import add_target_arguments, resolve_targets  # pyright: ignore[reportMissingImports]


CLAUDE_CMD = "claude"

os.environ["BASH_MAX_TIMEOUT_MS"] = "36000000"
os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "high"
os.environ["CI"] = "1"


def get_timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def run_task(target: str) -> Tuple[str, int, Optional[str]]:
    try:
        log_dir = os.path.join(target, "logs")
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, "filter_verify.jsonl")
        err_file = os.path.join(log_dir, "filter_verify.err")
        abs_target = os.path.abspath(target).replace("\\", "/")

        prompt = f"""Execute filter verification on the paper {abs_target}:

- /filter-verify

Paper Folder Path: {abs_target}
Output directory: {abs_target}"""

        print(f"[{get_timestamp()}] Starting: {target}")

        with open(log_file, "w", encoding="utf-8") as f, open(err_file, "w", encoding="utf-8") as ef:
            result = subprocess.run(
                [
                    CLAUDE_CMD,
                    "-p",
                    prompt,
                    "--allowedTools",
                    "Task,TaskOutput,Bash,Glob,Grep,ExitPlanMode,Read,Edit,Write,NotebookEdit,WebFetch,TodoWrite,WebSearch,KillShell,AskUserQuestion,Skill,EnterPlanMode,MCPSearch",
                    "--permission-mode",
                    "dontAsk",
                    "--output-format",
                    "stream-json",
                    "--verbose",
                ],
                stdout=f,
                stderr=ef,
                stdin=subprocess.DEVNULL,
                text=True,
            )

        return (target, result.returncode, None)

    except Exception as e:
        return (target, -1, str(e))


def main():
    parser = argparse.ArgumentParser(
        description="Batch runner for filter-verify with Claude Code.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=1,
        metavar="N",
        help="Number of parallel jobs (default: 1, sequential)",
    )
    add_target_arguments(parser)

    args = parser.parse_args()

    if args.jobs < 1:
        print("Error: Number of jobs must be at least 1")
        sys.exit(1)

    try:
        targets, selection_summary = resolve_targets(
            args.path,
            single=args.single,
            start=args.start,
            end=args.end,
            sort=args.sort,
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Starting batch execution for filter-verify...")
    print(f"Parallel jobs: {args.jobs}")
    print(selection_summary)
    print(f"Total targets: {len(targets)}")
    print()

    print("Targets:")
    for t in targets:
        print(f"  - {t}")
    print()

    results: Dict[str, Tuple[int, Optional[str]]] = {}

    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        future_to_target = {
            executor.submit(run_task, target): target for target in targets
        }

        for future in as_completed(future_to_target):
            target, exit_code, error = future.result()
            results[target] = (exit_code, error)

            if exit_code == 0:
                print(f"[{get_timestamp()}] ✓ Success: {target}")
            else:
                print(f"[{get_timestamp()}] ✗ Failed: {target} (Exit Code: {exit_code})")
                if error:
                    print(f"    Error: {error}")
                else:
                    err_file = os.path.join(target, "logs", "filter_verify.err")
                    print(f"    Check {err_file} for details")

    print()
    print("-" * 50)
    print("Batch processing complete.")
    print()

    success_count = sum(1 for code, _ in results.values() if code == 0)
    fail_count = len(results) - success_count
    failed_targets = [t for t, (code, _) in results.items() if code != 0]

    print(f"Summary: {success_count} succeeded, {fail_count} failed out of {len(targets)} total")

    if failed_targets:
        print()
        print("Failed targets:")
        for target in failed_targets:
            print(f"  - {target}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
