from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path

MARKER = "===EVAL_RESULT_JSON==="


def main() -> None:
    if len(sys.argv) != 2 or not os.environ.get("OUTPUT_DIR"):
        raise SystemExit("usage: evaluator_runner.py <evaluator.py>; OUTPUT_DIR is required")
    evaluator_path = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(evaluator_path.parent))
    try:
        spec = importlib.util.spec_from_file_location("naturebench_task_evaluator", evaluator_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import {evaluator_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        entrypoint = getattr(module, "run_evaluation", None) or getattr(module, "main", None)
        if entrypoint is None:
            raise RuntimeError("evaluator.py must define run_evaluation() or main()")
        result = entrypoint()
        print(MARKER, flush=True)
        print(json.dumps(result if isinstance(result, dict) else {}), flush=True)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
