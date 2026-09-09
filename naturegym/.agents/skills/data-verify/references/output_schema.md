# Output Schema: data_verify_result.json

The data-verify skill writes a single output file: `data_verify_result.json` in the paper folder. This file is a verification report for human review — it does not replace or modify `filter_result.json`.

---

## Top-Level Structure

```json
{
  "paper_id": "string",
  "verify_timestamp": "ISO 8601 datetime",

  "algorithm_boundary": { "..." },
  "checks": [ "..." ]
}
```

---

## algorithm_boundary

Records the Algorithm A boundary analysis from Phase 2. This serves as the foundation for Checks V1 and V4.

```json
"algorithm_boundary": {
  "algorithm_definition": "string (verbatim from task_info.algorithm)",
  "processing_pipeline": "string (concise description of A's pipeline derived from code analysis: data loading → [steps] → training → evaluation)",
  "file_classifications": [
    {
      "file": "string (path relative to repository root, e.g., 'data/traindata.csv')",
      "classification": "initial_state | data_preparation | algorithm_preprocessing_output | algorithm_output | external_resource | irrelevant",
      "reason": "string (why this classification, citing code evidence)"
    }
  ]
}
```

Notes:
- `file_classifications` covers all data-related files in the repository (not every file — skip `.git/`, documentation, CI configs unless they affect data)
- `processing_pipeline` should clearly mark where "data ends" and "algorithm begins"

---

## checks

Array of exactly 5 check results, one per check (V1–V5). Each check has a uniform structure:

```json
{
  "check_id": "V1 | V2 | V3 | V4 | V5",
  "check_name": "string",
  "status": "pass | fail | warning",
  "findings": [ "..." ]
}
```

### Status values

- **pass**: No issues found
- **warning**: Minor issues that should be reviewed but may not require changes
- **fail**: Issues that require correction before the data can be used downstream

### findings[] — per-check structures

Each check has its own finding structure. All findings share these common fields:

| Field | Type | Description |
|-------|------|-------------|
| `setting` | string | Setting name from `evaluation_settings[].name`, or `"global"` for cross-setting issues |
| `issue_type` | string | Check-specific issue type. Known types are listed per check below; new types may be added using `snake_case` naming when existing types do not fit. |
| `severity` | string (enum) | `"high"` = must fix before downstream use; `"medium"` = should fix for correctness; `"low"` = minor, nice to fix |
| `description` | string | What is wrong and how to fix it: summarize the problem, then briefly state the required action (e.g., "remove from file list", "rewrite description to exclude X", "update count") |
| `evidence` | string | Supporting citations and reasoning: code paths, file contents, paper sections, and why the recommended change is correct |

**Field content principle**: For findings with `recommended_value`, the value must be the **replacement content itself** — text that verify-apply can directly assign to the target field. Do not put explanations, observations, or instructions in `recommended_value`; those belong in `description` (problem + action) and `evidence` (justification).

Additional fields vary by check:

#### V1: D_dev Component Boundary

```json
{
  "setting": "string",
  "issue_type": "string (known types: surplus_component, missing_component, wrong_classification)",
  "description": "string",
  "field": "string (JSON path in filter_result.json, e.g., 'task_info.data.evaluation_settings[0].d_dev.source.instruction')",
  "current_value": "string (current value summary)",
  "recommended_value": "string (what it should be)",
  "evidence": "string"
}
```

#### V2: Evaluation Setting Validity

```json
{
  "setting": "string (or 'settings[0]+settings[1]' for merge cases)",
  "issue_type": "string (known types: should_merge, should_split, should_remove, scope_too_narrow, invalid_eval_method, missing_setting, evaluation_alignment_broken, infeasible_eval_mechanism)",
  "description": "string",
  "evidence": "string"
}
```

#### V3: Separability Correctness

```json
{
  "setting": "string",
  "issue_type": "string (known types: algorithm_in_split_procedure, wrong_feature_scope, missing_field_disposition, wrong_sample_count, parameter_placeholder, incorrect_split_specification, difficulty_mismatch, misplaced_eval_operation, inference_scoring_mismatch)",
  "description": "string",
  "field": "string (JSON path)",
  "current_value": "string",
  "recommended_value": "string",
  "evidence": "string"
}
```

#### V4: Data Directory Integrity

```json
{
  "setting": "string",
  "issue_type": "string (known types: algorithm_artifact, missing_file, irrelevant_file)",
  "file": "string (path under data/, e.g., 'data/setting_name/selXcols.csv')",
  "classification": "string (from algorithm_boundary classification)",
  "recommended_action": "delete | add",
  "evidence": "string"
}
```

#### V5: Description & Evidence Consistency

V5 findings always target **task_info** fields, not filter_process evidence fields. Evidence errors are only reported when they propagate to task_info (see V5.2 in check_rules.md).

```json
{
  "setting": "string",
  "issue_type": "string (known types: algorithm_in_description, numerical_error, factual_error, stale_reference, cross_reference_mismatch)",
  "description": "string",
  "field": "string (JSON path in task_info, e.g., 'task_info.data.evaluation_settings[0].d_dev.description')",
  "current_value": "string (what the task_info field currently says)",
  "recommended_value": "string (what the field should be changed to)",
  "evidence": "string"
}
```

---

## Example (abbreviated)

```json
{
  "paper_id": "s42256-020-00249-z",
  "verify_timestamp": "2026-03-24T10:00:00Z",

  "algorithm_boundary": {
    "algorithm_definition": "Random Forest (two-class) and SVM with RBF kernel (three-class) classifiers with recursive feature elimination (RFE)...",
    "processing_pipeline": "Load traindata.csv → shuffle → remap labels (task def) → RFE feature selection (Algorithm A) → train_test_split → GridSearchCV training → evaluate",
    "file_classifications": [
      { "file": "data/traindata.csv", "classification": "initial_state", "required": null, "reason": "Raw MOF dataset with 207 entries, loaded as first step" },
      { "file": "data/selXcols-svmLinear-2class.csv", "classification": "algorithm_preprocessing_output", "required": null, "reason": "Output of RFE feature selection step, which is part of Algorithm A" },
      { "file": "models/rf_ml_2class.pkl", "classification": "algorithm_output", "required": null, "reason": "Trained model weights from Algorithm A" }
    ]
  },

  "checks": [
    {
      "check_id": "V1",
      "check_name": "D_dev Component Boundary",
      "status": "fail",
      "findings": [
        {
          "setting": "Burtch dataset cross-validation (two-class model)",
          "issue_type": "surplus_component",
          "severity": "high",
          "description": "selXcols-svmLinear-2class.csv is listed as D_dev component but is an RFE output (Algorithm A intermediate)",
          "field": "task_info.data.evaluation_settings[0].verification.separability.dev_eval.d_dev_files",
          "current_value": "includes selXcols-svmLinear-2class.csv",
          "recommended_value": "remove selXcols-svmLinear-2class.csv; D_dev should only contain traindata.csv",
          "evidence": "RFE is explicitly part of Algorithm A name. selXcols file is generated by SVM-linear RFE process, not present in initial state."
        }
      ]
    }
  ]
}
```
