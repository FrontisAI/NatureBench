# Output Schema

The task-verify skill outputs `task_verify_result.json` with the following structure.

## Schema

```json
{
  "overall_status": "pass | failed",
  "failed_checks": [
    {
      "check_id": "string",
      "issue": "string",
      "location": "string"
    }
  ],
  "warnings": [
    {
      "check_id": "string",
      "issue": "string",
      "location": "string"
    }
  ],
  "summary": {
    "total_checks": 36,
    "passed": 0,
    "failed": 0,
    "warnings": 0
  },
  "dynamic_test": {
    "status": "pass | failed",
    "baseline_score": {},
    "ground_truth_score": {},
    "robustness_test": {
      "missing_file": "error_result | crash | false_scores",
      "empty_file": "error_result | crash | false_scores",
      "wrong_format": "error_result | crash | false_scores",
      "invalid_values": "error_result | crash | false_scores",
      "wrong_sample_count": "error_result | crash | false_scores",
      "misaligned_ids": "error_result | crash | false_scores | skipped"
    },
    "error": "string | null"
  }
}
```

## Field Descriptions

### overall_status
- **Type**: string
- **Values**: "pass" | "failed"
- **Description**: Overall verification status. "pass" if all checks passed (warnings allowed), "failed" if any check failed.

### failed_checks
- **Type**: array of objects
- **Description**: List of checks that failed. Empty if all checks passed.
- **Object fields**:
  - `check_id`: Check identifier (e.g., "C1.3")
  - `issue`: Human-readable description of the problem
  - `location`: File paths and line numbers where the issue was found

### warnings
- **Type**: array of objects
- **Description**: List of checks that passed but raised warnings (non-critical issues).
- **Object fields**: Same as failed_checks

### summary
- **Type**: object
- **Description**: Summary statistics
- **Fields**:
  - `total_checks`: Always 34
  - `passed`: Number of checks that passed
  - `failed`: Number of checks that failed
  - `warnings`: Number of warnings raised

### dynamic_test
- **Type**: object
- **Description**: Results from Phase 4 dynamic testing
- **Fields**:
  - `status`: "pass" | "failed"
  - `baseline_score`: Object mapping instance names to metric scores (e.g., `{"instance1": {"RMSE": 0.45, "MAE": 0.32}}`)
  - `ground_truth_score`: Object mapping instance names to metric scores when ground truth is used as perfect prediction input. Null or absent for Oracle-type tasks where C4.8 is skipped.
  - `robustness_test`: Object recording evaluator behavior for each malformed input type. Values are "error_result" (preferred — returned null metrics with error message), "crash" (unhandled exception), "false_scores" (silently produced numeric scores), or "skipped" (test not applicable, e.g., no sample IDs for misaligned_ids test).
  - `error`: Error message if dynamic test failed, null otherwise

## Design Principles

1. **Brevity**: Only report failures and warnings. Passed checks are not listed to reduce noise.

2. **Actionability**: Each issue includes specific file paths and line numbers so users can quickly locate and fix problems.

3. **Completeness**: All phases execute even if earlier phases fail, so users get a complete picture of all issues in one run.

## Example Output

```json
{
  "overall_status": "failed",
  "failed_checks": [
    {
      "check_id": "C1.3",
      "issue": "Metric names inconsistent: README has ['RMSE', 'MAE'], evaluator.py has ['rmse', 'mae']",
      "location": "problem/README.md:45, evaluation/evaluator.py:12"
    },
    {
      "check_id": "C2.1",
      "issue": "Paper reference found in README: 'Nature Machine Intelligence' at line 8",
      "location": "problem/README.md:8"
    }
  ],
  "warnings": [
    {
      "check_id": "C3.7",
      "issue": "Metric 'R2' in README lacks baseline score in metadata.json",
      "location": "problem/README.md:52, metadata.json"
    }
  ],
  "summary": {
    "total_checks": 36,
    "passed": 32,
    "failed": 2,
    "warnings": 1
  },
  "dynamic_test": {
    "status": "pass",
    "baseline_score": {
      "bbbp": {"ROC-AUC": 52.3},
      "tox21": {"ROC-AUC": 48.7},
      "bace": {"ROC-AUC": 51.2}
    },
    "ground_truth_score": {
      "bbbp": {"ROC-AUC": 100.0},
      "tox21": {"ROC-AUC": 100.0},
      "bace": {"ROC-AUC": 100.0}
    },
    "robustness_test": {
      "missing_file": "error_result",
      "empty_file": "error_result",
      "wrong_format": "error_result",
      "invalid_values": "error_result",
      "wrong_sample_count": "error_result",
      "misaligned_ids": "skipped"
    },
    "error": null
  }
}
```
