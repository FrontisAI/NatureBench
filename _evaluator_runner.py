"""Subprocess wrapper for running evaluator.py in isolation.

Usage: python _evaluator_runner.py <evaluator_script_path>
Reads OUTPUT_DIR from env (passed by parent eval_service).
Calls run_evaluation() or main() and prints result dict as JSON
after a marker line so parent can extract it from stdout.
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys
import traceback

MARKER = "===EVAL_RESULT_JSON==="

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: _evaluator_runner.py <evaluator_script>\n")
        sys.exit(2)
    evaluator_path = sys.argv[1]
    if not os.path.exists(evaluator_path):
        sys.stderr.write(f"evaluator script not found: {evaluator_path}\n")
        sys.exit(2)
    if not os.environ.get("OUTPUT_DIR"):
        sys.stderr.write("OUTPUT_DIR env var is required\n")
        sys.exit(2)
    eval_dir = os.path.dirname(os.path.abspath(evaluator_path))
    if eval_dir not in sys.path:
        sys.path.insert(0, eval_dir)
    try:
        spec = importlib.util.spec_from_file_location(
            f"evaluator_subprocess_{os.path.basename(eval_dir)}", evaluator_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"could not load spec from {evaluator_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "run_evaluation"):
            entry = mod.run_evaluation
        elif hasattr(mod, "main"):
            entry = mod.main
        else:
            raise RuntimeError("evaluator.py must define run_evaluation() or main()")
        result = entry()
        if not isinstance(result, dict):
            result = {}
        print(MARKER, flush=True)
        print(json.dumps(result), flush=True)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
