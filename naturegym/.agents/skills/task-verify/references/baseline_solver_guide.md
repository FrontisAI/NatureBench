# Baseline Solver Generation Guide

This guide explains how to generate baseline solvers for dynamic testing (Phase 4).

## Strategy

1. **Copy run.py template from README Section 6**: Already has correct INSTANCES, DATA_DIR, OUTPUT_DIR
2. **Fill in logic**: Read README Section 5 (output format) and data_description to understand data format, then write data loading and baseline prediction code
3. **Run `scripts/run_baseline_test.py`**: Execute baseline solver + evaluator, get actual scores
4. **Goal**: 100% coverage - every task package must complete dynamic testing

## Step 1: Get run.py Template

Read README Section 6 (Submission Guidelines). It contains a run.py template with:
- Correct `DATA_DIR` and `OUTPUT_DIR` environment variables
- Correct `INSTANCES` list
- Correct directory structure

Copy this template as the starting point for the baseline solver.

## Step 2: Fill In Logic

Read the following to understand the task:
- **README Section 2** (Task Objective): What is the task? Classification, regression, generation?
- **README Section 5** (Output Format): Exact filename, format, shape, dtype
- **data_description.md**: Data file formats per instance
- **problem/data/**: Actual data files (use ls/Glob to check formats)

Then fill in three parts in run.py:

1. **Data loading**: Read training data and test data (NPY, CSV, HDF5, etc.)
2. **Baseline prediction**: Generate simplest possible predictions
3. **Output saving**: Save in exact format evaluator expects

**Code organization**:
- Simple tasks: Single `run.py` file (50-150 lines) is sufficient
- Complex tasks: You may create additional files in workspace/ (e.g., `utils.py`, `data_loader.py`) if needed for clarity, but keep it minimal

## Step 3: Run Test (run_baseline_test.py)

```bash
python scripts/run_baseline_test.py <task_package_path> <workspace_path>
```

**What it does**:
1. Sets DATA_DIR and OUTPUT_DIR environment variables
2. Runs workspace/run.py (baseline solver)
3. Runs evaluation/evaluator.py on baseline outputs
4. Returns actual scores from score.json

**Output**: JSON with scores per instance
```json
{
  "instance1": {"Accuracy": 0.13},
  "instance2": {"Accuracy": 0.07}
}
```

**Timeouts**: Solver 5min, Evaluator 10min

**Exit codes**: 0 = success, 1 = failure (check stderr)

## Key Principles

1. **Simplicity**: Baseline should be as simple as possible while being functional
2. **Correctness**: Must match README output specification exactly
3. **Robustness**: Should handle all instances without crashing
4. **Performance irrelevant**: Baseline can have terrible performance - that's expected

## Running Baseline Test

Use `scripts/run_baseline_test.py` to execute baseline solver and evaluator:

```bash
python scripts/run_baseline_test.py <task_package_path> <workspace_path>
```

**What it does**:
1. Runs baseline solver (workspace/run.py) with OUTPUT_DIR set
2. Runs evaluator (evaluation/evaluator.py) on baseline outputs
3. Returns actual scores from score.json

**Output**: JSON with scores per instance
```json
{
  "instance1": {"RMSE": 0.45, "MAE": 0.32},
  "instance2": {"RMSE": 0.52, "MAE": 0.38}
}
```

**Timeouts**:
- Baseline solver: 5 minutes
- Evaluator: 10 minutes

**Exit codes**:
- 0: Success
- 1: Failure (check stderr for details)

## Verification

After generating baseline solver:

1. **C4.2**: Run it on all instances - must complete without errors
2. **C4.3**: Check output files exist and match specification
3. **C4.4**: Run evaluator on outputs - must complete without errors
4. **C4.5**: Check evaluator produces valid score.json
5. **C4.6**: Sanity check scores (not NaN/Inf, within valid range)
6. **C4.7**: Verify solver conforms to README interface

## Common Pitfalls

1. **Hardcoded paths**: Use relative paths or environment variables
2. **Missing dependencies**: Only use standard libraries (numpy, pandas, scipy) unless task requires specific libraries
3. **Output format mismatch**: Carefully match README specification (column names, data types, file format)
4. **Instance name mismatch**: Use exact instance names from problem/data/
5. **Missing error handling**: Baseline should not crash on edge cases

## When Manual Generation is Required

- Complex domain-specific tasks (protein folding, molecular dynamics)
- Non-standard output formats (custom binary, special graph structures)
- Tasks requiring domain knowledge (physics simulations, chemical reactions)
- Tasks with unusual data formats (3D meshes, point clouds, spectrograms)

In these cases, the skill must:
1. Carefully read all documentation
2. Inspect actual data files
3. Write conservative baseline that produces valid output
4. Test thoroughly before proceeding to evaluation

## Evaluator Correctness Test (C4.8)

After baseline testing (C4.1–C4.7), construct a "perfect prediction" to verify the evaluator's scoring logic.

### How to Construct Perfect Predictions

1. **Read evaluator.py** to understand:
   - `load_ground_truth()`: how ground truth is loaded (format, columns, shape)
   - `load_and_validate()`: expected solver output format (filename, columns, dtype, shape)
   - `calculate_metrics()`: what computation is performed

2. **Write a script** that reads ground truth and converts it to solver output format:

   | Task Type | Conversion |
   |-----------|------------|
   | Classification (label output) | Copy labels directly |
   | Classification (probability output) | One-hot: P=1.0 for true class, 0.0 for others |
   | Regression | Copy target values directly |
   | Ranking | Produce perfect rank ordering |
   | Generation (reference set) | Output the reference set itself |
   | Custom | Infer from calculate_metrics() what maximizes/minimizes each metric |

3. **Save** to temporary output directory matching README Section 5 spec (filename, path pattern)

4. **Run** using `scripts/run_baseline_test.py` — same as baseline test

5. **Verify** scores are near-perfect:
   - Accuracy/F1/AUC/Precision/Recall: ≥0.99
   - RMSE/MAE/MSE: ≤1e-6
   - Pearson/Spearman correlation: ≥0.99
   - No clear perfect value (FCD, perplexity): must be substantially better than baseline

### When to Skip

- **Oracle-type tasks**: evaluator wraps oracle/scorer, no static ground truth → skip
- **Distribution-based generation**: quality measured against distribution, not point-wise → skip unless clear perfect input exists

## Evaluator Robustness Test (C4.9)

Test how the evaluator handles invalid solver outputs. Run on ONE representative instance only.

### 6 Malformed Input Tests

| Test | How to Construct |
|------|------------------|
| Missing file | Delete the expected output file |
| Empty file | Create 0-byte file at expected path |
| Wrong format | Swap CSV↔plaintext, or NPY↔CSV |
| Invalid values | Correct format but fill numeric fields with `float('nan')` or `float('inf')` |
| Wrong sample count | Correct format but half (or double) the expected row count |
| Misaligned IDs | Correct format and count but sample IDs don't match ground truth (shuffle/duplicate/fabricate). Skip if output has no sample IDs. |

### Expected Evaluator Behavior

For each malformed input, the evaluator should do ONE of:
- **PREFERRED**: Return error_result dict with null metrics and error message
- **ACCEPTABLE**: Exit with non-zero code and clear stderr error

**Failures**:
- Returns numeric scores (not null) → evaluator silently accepts garbage → **FAIL**
- Unhandled exception crash with no result → **WARNING** (functional but not robust)
