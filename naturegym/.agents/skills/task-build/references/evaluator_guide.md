# Phase 3: Evaluator Guide

## Objective

Generate `evaluation/evaluator.py` — the automated judge that scores agent submissions by reading output files from `workspace/output/`. The evaluator must be correct, robust, and thoroughly tested.

## Information Sources

1. **`problem/README.md`**: Output format specification and instance names (Section 5), metric definitions (Section 4)
2. **filter_result.json**: `task_info.metrics` (names, score_source), evaluation settings
3. **`repositories/`**: Author's evaluation/metric code — reference for implementation logic, edge cases, and domain-specific adjustments
4. **`problem/data_description.md`**: Solver-visible data formats, for understanding output structure and alignment
5. **`evaluation/ground_truth/`**: Actual ground truth files; reference filter_result.json's y_ref-related fields for format and semantics
6. **Paper text/figures/tables**: Metric definitions when README description is insufficient
7. **[references/Dockerfile.base.v3](Dockerfile.base.v3)**: Pre-installed library versions in the target environment — check before using version-sensitive APIs to ensure compatibility

## Critical Constraints

1. **Output Reading**: The evaluator reads output files from `workspace/output/`. It does NOT import or execute any agent code. The agent code runs separately via subprocess; the evaluator only reads its file output.
2. **Validation**: Before scoring, the evaluator MUST validate each output file — checking existence, format, shape, dtype, and value range. On validation failure, return an error result with a descriptive message.
3. **Metric Consistency**: Metric names in evaluator output MUST match README exactly
4. **No Averaging**: For multi-instance tasks, return separate metric dictionaries per instance; do NOT average across instances
5. **Full Coverage**: The evaluator must support all surviving settings — settings cannot be dropped at this phase
6. **No NaN in JSON**: NEVER use `float("nan")` or `np.nan` as metric values. JSON does not support NaN. Use `null` for missing/invalid metrics, or use sentinel values like `-1` or `0` with clear documentation

## Output Format

Generate `evaluation/evaluator.py`:

```python
import os
import json
import numpy as np
# [Import other libraries as needed]

# Setup Paths
EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
GROUND_TRUTH_DIR = os.path.join(EVAL_DIR, "ground_truth")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR")  # Must be provided by pipeline
if not OUTPUT_DIR:
    raise RuntimeError("OUTPUT_DIR environment variable is required")

# Output specification (must match README Section 5)
OUTPUT_FILE = "output.npy"  # [Populate: output filename from README]
INSTANCES = [...]                # [Populate: instance names from README]
METRIC_NAMES = ["MetricName"]   # [Populate: metric names from README]
# Note: When instances have different metric sets (per README), replace METRIC_NAMES
# with a per-instance mapping (e.g., dict) and adapt the functions below accordingly.


class ValidationError(Exception):
    """Raised when output file fails validation."""
    pass


def error_result(error_msg):
    """Return a result dict with null metrics and error info.
    
    IMPORTANT: Use None (null in JSON), never float("nan") or np.nan.
    JSON does not support NaN values.
    """
    result = {name: None for name in METRIC_NAMES}
    result["error"] = str(error_msg)
    return result


def load_and_validate(instance_name):
    """
    Load the output file for an instance and validate.

    Args:
        instance_name: Name of the task instance.

    Returns:
        The loaded and validated predictions.

    Raises:
        ValidationError: If the output file is missing or has wrong
            format, shape, dtype, or values out of range.
    """
    pred_file = os.path.join(OUTPUT_DIR, instance_name, OUTPUT_FILE)

    # Check file exists
    if not os.path.exists(pred_file):
        raise ValidationError(f"Output file not found: {pred_file}")

    # Load predictions
    # [Implement loading based on file format:
    #  .npy → np.load(pred_file)
    #  .csv → pd.read_csv(pred_file)
    #  .json → json.load(open(pred_file)) ]

    # Validate shape, dtype, value range
    # [Implement validation based on README Section 5 specification]

    return predictions


def calculate_metrics(predictions, ground_truth):
    """
    Calculate evaluation metrics.

    Args:
        predictions: Validated predictions loaded from output file.
        ground_truth: The loaded ground truth for this instance.

    Returns:
        dict: {metric_name: metric_value} matching README metric names exactly.
    """
    # [Implement metric calculations]
    return {"MetricName": 0.0}


def run_evaluation():
    """Run the complete evaluation pipeline."""
    results = {}

    for instance_name in INSTANCES:
        print(f"\n{'='*60}")
        print(f"Evaluating instance: {instance_name}")
        print(f"{'='*60}")

        try:
            # Load and validate output
            predictions = load_and_validate(instance_name)

            # Load ground truth
            ground_truth = ...  # Load from GROUND_TRUTH_DIR/{instance_name}/

            # Calculate metrics
            scores = calculate_metrics(predictions, ground_truth)
            results[instance_name] = scores
            print(f"Results: {scores}")

        except ValidationError as e:
            print(f"[Validation Error] {instance_name}: {e}")
            results[instance_name] = error_result(f"Validation: {e}")

        except Exception as e:
            print(f"[Error] {instance_name}: {e}")
            import traceback
            traceback.print_exc()
            results[instance_name] = error_result(e)

    return results


if __name__ == "__main__":
    metrics = run_evaluation()
    print("\n=== Final Results ===")
    print(json.dumps(metrics, indent=2))
    with open("score.json", "w") as f:
        json.dump(metrics, f, indent=2)
```

## Design Process

### Step 1: Reference Author Implementation

Before implementing metrics, search `repositories/` for evaluation code (e.g., `evaluate.py`, `eval.py`, `metrics.py`). If found:
- Study the computation logic, edge case handling, and domain-specific adjustments
- Use as a reference — do NOT directly copy code (IP concerns)

### Step 2: Implement Metrics

The evaluation pattern depends on the y_ref type: **Label** → compare predictions against static ground truth; **Oracle** → run oracle/scorer on outputs (may also use test inputs); **Distribution** → compute distributional metrics on generated sample set.

For each metric defined in README, choose the most appropriate implementation:
- Reference author code (if found in Step 1) combined with your own understanding of the metric definition
- Use standard or domain-specific library implementations where they are accurate and more reliable than manual code
- If no suitable library exists, implement manually based on the mathematical definition
- Handle edge cases consistently with author implementation

**Handling Missing Values in Multi-Task Scenarios:**
- Multi-task datasets (e.g., molecular property prediction with multiple targets) often have missing labels (NaN in ground truth)
- When computing per-task metrics, skip samples where ground truth is NaN for that task
- When aggregating across tasks, use `np.nanmean()` internally for computation
- **CRITICAL**: The final metric value written to JSON must NEVER be NaN. If all tasks have insufficient valid samples:
  - Return `None` (not `float("nan")`) to indicate the metric cannot be computed
  - Add an error message explaining why (e.g., "Insufficient valid samples across all tasks")
- Example pattern:
  ```python
  per_task_scores = []
  for task_idx in range(n_tasks):
      valid_mask = ~np.isnan(ground_truth[:, task_idx])
      if valid_mask.sum() == 0:
          continue  # Skip tasks with no valid labels
      task_score = compute_metric(predictions[valid_mask, task_idx], 
                                   ground_truth[valid_mask, task_idx])
      per_task_scores.append(task_score)
  
  if len(per_task_scores) == 0:
      return None  # Not float("nan")
  return float(np.mean(per_task_scores))
  ```

### Step 3: Implement load_and_validate

Based on the Output Format section (Section 5) in `problem/README.md`:
- Implement file loading logic matching the specified format
- Validate shape, dtype, and value range as specified in the README
- On validation failure, raise `ValidationError` with a descriptive message
- Ensure alignment with ground truth (same sample order or matched by IDs)

### Step 4: Ground Truth Loading

- Load and parse ground truth into the format needed for metric calculation
- If metric calculation requires auxiliary data beyond ground truth (e.g., class counts, sample weights), place it in `evaluation/` during task-build:
    - Per-instance auxiliary data → `evaluation/ground_truth/{instance_name}/` (alongside y_ref files)
    - Shared auxiliary data → `evaluation/shared/`

### Step 5: Error Handling

- If one instance fails (validation or scoring), continue with others
- On failure, return all metric keys with `None` values plus an `"error"` key

## Verification (CRITICAL)

The evaluator MUST be verified before delivery:

1. **Metric Logic Verification**: Test each metric function with known inputs and expected outputs to verify computational correctness.
2. **Smoke Test**: Create dummy output files in the correct format:
   - Create `workspace/output/{instance_name}/` directories
   - Write dummy prediction files (e.g., zeros, random values) matching the README Output Format
   - Run the evaluator and verify:
     - Executes without errors for all instances
     - All metric keys present, values in expected ranges, no NaN/Inf (use `None` for invalid metrics)
     - `score.json` saved correctly and is valid JSON (test with `json.load()`)
   - Also test validation: create a malformed output file (wrong shape) and verify `ValidationError` is raised with a clear message
3. **Author Code Comparison** (if available): The author's evaluation code usually cannot be used directly due to input format differences. Adapt by: (a) adjusting the author's script to accept our output format, (b) converting our output to the author's expected format, or (c) extracting only the author's core metric computation logic. Pass the same inputs to both the author's metric implementation and`evaluator.py`. Results should match or differences be explainable.
4. **Paper Score Reproduction** (if feasible): Search `repositories/` for Algorithm A's prediction outputs (e.g., `predictions.csv`, `results.npy`, saved model outputs). If found, convert them to the evaluator's expected format and run the evaluator. Compare the resulting scores against the paper's reported values. Scores should match closely; significant discrepancies indicate bugs in the evaluator or ground truth extraction.
5. **Cleanup**: Delete the dummy output files, `score.json`, and any temporary files after testing. Remove the `workspace/output/{instance_name}/` directories created during testing, as well as the `evaluation/__pycache__/` directory and any `.pyc` files generated during evaluator execution. This cleanup is required even if tests fail — always clean up before finishing Phase 3.
6. **Update Build Record**: Record implementation sources in `task_build.phase_3.implementation` and verification results in `task_build.phase_3.verification`.

## Dependencies

The evaluator's dependencies are managed by `environment/Dockerfile.v3` (Phase 5). When writing the evaluator, follow these rules to avoid downstream compatibility issues:

### Library Selection Rules

1. **Prefer base image libraries**: Before importing any library, check [references/Dockerfile.base.v3](Dockerfile.base.v3) for what is already pre-installed. The base image includes a comprehensive scientific Python stack (numpy, scipy, pandas, scikit-learn, torch, transformers, rdkit, biopython, etc.). **If the base already provides equivalent functionality, use the base library — do NOT add a new dependency.**

2. **Check API compatibility**: When using any library, verify that the API calls you use are compatible with the specific version in the base image:
   - numpy 2.x: `np.bool`, `np.int`, `np.float`, `np.complex`, `np.object`, `np.str` are removed — use Python builtins (`bool`, `int`, `float`)
   - pandas 2.x: `DataFrame.append()` is removed — use `pd.concat()`
   - scikit-learn 1.6.x: check for renamed parameters or deprecated functions
   - When adapting author code from repositories/, these old API patterns are common and must be updated

3. **Minimize non-base dependencies**: The evaluator is Tier 1 — its imports are non-negotiable hard requirements. Every non-base library you import becomes a package that must be installed, version-checked, and maintained. If you can implement the same functionality using base libraries (even if it takes a few more lines of code), **do that instead of adding a dependency**.

4. **Note non-base imports explicitly**: If the evaluator genuinely needs a library not in the base image (e.g., a domain-specific metric library), add a comment in the evaluator noting the dependency, so Phase 5 (Environment) can include it in the Dockerfile.v3 with a compatible version.

### Common Patterns

| Instead of importing... | Use base library... |
|---|---|
| `fcd` / `molsets` (molecular metrics) | `rdkit` + manual implementation |
| `elmoformanylangs` (ELMo embeddings) | `transformers` (already in base) |
| Specialized metric packages | `sklearn.metrics` + manual implementation |
| `tensorflow` (for simple ops) | `torch` (already in base) |

