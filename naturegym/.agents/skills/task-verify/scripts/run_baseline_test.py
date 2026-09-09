#!/usr/bin/env python3
"""
Run baseline solver and evaluator to get actual scores.

Usage:
    python run_baseline_test.py <task_package_path> <workspace_path>

Returns:
    Prints score.json content to stdout if successful.
    Returns exit code 1 if execution fails.
"""

import os
import sys
import json
import subprocess
import tempfile


def run_baseline_solver(task_package_path, workspace_path, output_dir):
    """Run baseline solver and generate predictions."""
    run_script = os.path.join(workspace_path, 'run.py')
    if not os.path.exists(run_script):
        print(f"ERROR: run.py not found in {workspace_path}", file=sys.stderr)
        return False

    env = os.environ.copy()
    env['OUTPUT_DIR'] = output_dir
    env['DATA_DIR'] = os.path.join(task_package_path, 'problem', 'data')

    try:
        result = subprocess.run(
            ['python3', run_script],
            cwd=workspace_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )

        if result.returncode != 0:
            print(f"ERROR: Baseline solver failed: {result.stderr}", file=sys.stderr)
            return False

        return True
    except subprocess.TimeoutExpired:
        print("ERROR: Baseline solver timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR: Failed to run baseline solver: {e}", file=sys.stderr)
        return False


def run_evaluator(task_package_path, output_dir):
    """Run evaluator and get scores."""
    evaluator_script = os.path.join(task_package_path, 'evaluation', 'evaluator.py')
    if not os.path.exists(evaluator_script):
        print(f"ERROR: evaluator.py not found", file=sys.stderr)
        return None

    env = os.environ.copy()
    env['OUTPUT_DIR'] = output_dir

    try:
        result = subprocess.run(
            ['python3', evaluator_script],
            cwd=os.path.dirname(evaluator_script),
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            print(f"ERROR: Evaluator failed: {error_msg}", file=sys.stderr)
            return None

        # Read score.json - check both evaluator cwd and output_dir
        eval_dir = os.path.dirname(evaluator_script)
        score_candidates = [
            os.path.join(eval_dir, 'score.json'),
            os.path.join(output_dir, 'score.json'),
        ]
        score_file = None
        for candidate in score_candidates:
            if os.path.exists(candidate):
                score_file = candidate
                break

        if score_file is None:
            print(f"ERROR: score.json not generated (checked: {score_candidates})", file=sys.stderr)
            return None

        with open(score_file, 'r') as f:
            scores = json.load(f)

        # Cleanup: remove score.json from evaluator cwd if it was written there
        eval_score = os.path.join(eval_dir, 'score.json')
        if os.path.exists(eval_score):
            os.remove(eval_score)

        return scores
    except subprocess.TimeoutExpired:
        print("ERROR: Evaluator timed out", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Failed to run evaluator: {e}", file=sys.stderr)
        return None


def main():
    if len(sys.argv) != 3:
        print("Usage: python run_baseline_test.py <task_package_path> <workspace_path>", file=sys.stderr)
        sys.exit(1)

    task_package_path = sys.argv[1]
    workspace_path = sys.argv[2]

    # Create temporary output directory
    with tempfile.TemporaryDirectory() as output_dir:
        # Step 1: Run baseline solver
        print("Running baseline solver...", file=sys.stderr)
        if not run_baseline_solver(task_package_path, workspace_path, output_dir):
            sys.exit(1)

        # Step 2: Run evaluator
        print("Running evaluator...", file=sys.stderr)
        scores = run_evaluator(task_package_path, output_dir)
        if scores is None:
            sys.exit(1)

        # Output scores as JSON
        print(json.dumps(scores, indent=2))


if __name__ == '__main__':
    main()
