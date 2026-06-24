#!/usr/bin/env python3
"""
Batch runner for dockerfile-fix with Claude Code.

Usage:
    python batch_dockerfile_fix.py [-j N] [--dockerfile-name NAME] <parent_folder>
    python batch_dockerfile_fix.py [-j N] [--dockerfile-name NAME] --single <task_package_dir>
    python batch_dockerfile_fix.py [-j N] [--dockerfile-name NAME] --start 11 --end 20 <parent_folder>

Example:
    python batch_dockerfile_fix.py -j 4 pass
    python batch_dockerfile_fix.py --single pass/s42256-021-00325-y
    python batch_dockerfile_fix.py --start 11 --end 20 pass
"""

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import partial
from typing import Dict, Optional, Tuple

from batch_target_utils import add_target_arguments, resolve_targets  # pyright: ignore[reportMissingImports]


CLAUDE_CMD = "claude"

os.environ["BASH_MAX_TIMEOUT_MS"] = "36000000"
os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "high"
os.environ["CI"] = "1"


def get_timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def run_task(target: str, dockerfile_name: str) -> Tuple[str, int, Optional[str]]:
    try:
        env_dir = os.path.join(target, "environment")
        verify_result = os.path.join(env_dir, "verify_result.txt")
        packages_json = os.path.join(env_dir, "packages.json")
        dockerfile_path = os.path.join(env_dir, dockerfile_name)

        missing_files = []
        for required in (verify_result, packages_json, dockerfile_path):
            if not os.path.isfile(required):
                missing_files.append(required)
        if missing_files:
            return (
                target,
                -1,
                "Missing required file(s): " + ", ".join(missing_files),
            )

        log_dir = os.path.join(target, "logs")
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, "dockerfile_fix.jsonl")
        err_file = os.path.join(log_dir, "dockerfile_fix.err")
        abs_target = os.path.abspath(target).replace("\\", "/")

        prompt = f"""/dockerfile-fix

Task Package Path: {abs_target}
Dockerfile Name: {dockerfile_name}"""

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
        description="Batch runner for dockerfile-fix with Claude Code.",
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
    parser.add_argument(
        "--dockerfile-name",
        default="Dockerfile.v3",
        help="Dockerfile name under each target's environment directory (default: Dockerfile.v3)",
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

    print("Starting batch execution for dockerfile-fix...")
    print(f"Parallel jobs: {args.jobs}")
    print(f"Dockerfile name: {args.dockerfile_name}")
    print(selection_summary)
    print(f"Total targets: {len(targets)}")
    print()

    print("Targets:")
    for t in targets:
        print(f"  - {t}")
    print()

    results: Dict[str, Tuple[int, Optional[str]]] = {}

    run_target = partial(run_task, dockerfile_name=args.dockerfile_name)
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        future_to_target = {
            executor.submit(run_target, target): target for target in targets
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
                    err_file = os.path.join(target, "logs", "dockerfile_fix.err")
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
