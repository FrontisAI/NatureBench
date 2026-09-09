# Apply Rules: Verification → filter_result.json

Maps each verification check type to the concrete modification operation on filter_result.json.

> **Note:** For any unclear concepts, operations, requirements, or explanations during implementation or adjustment, refer to the documentation in the `paper-filter` and `data-check` skills.

---

## Filter-Verify Corrections

Filter-verify corrections have a uniform structure: `{ path, action, current, recommended, reason, evidence }`.

### Field-Level (C4–C9)

| action | operation |
|--------|-----------|
| `update` | Set the value at `path` to `recommended` |
| `add` | Insert `recommended` at `path` (for array items: append; for object keys: add key) |
| `remove` | Delete the element at `path` |

`path` uses dot notation relative to filter_result.json root (e.g., `task_info.metrics`, `task_info.data.evaluation_settings[0].d_dev.description`).

When `recommended` contains a JSON-formatted string (starts with `{` or `[`), parse it as JSON before inserting.

### Judgment Override (C1–C3)

When `verdict.override` is not null:

1. Set `final_result.passed` to `false`
2. Set `final_result.stopped_at` to the rule indicated in `override.rule` (format: `"Level 1 - Rule {rule}"`)
3. Update `final_result.decision_summary` to include `override.reason`
4. In `filtering_process`, find the level/rule matching `override.rule` and set its `passed` to `false`
5. If `override.category` is provided, update the corresponding rule's `category` field

---

## Data-Verify Findings

Data-verify findings vary by check. Each check type maps to a different operation.

### V1: D_dev Component Boundary

Finding fields: `field`, `current_value`, `recommended_value`

| issue_type | operation |
|------------|-----------|
| `surplus_component` | Remove the component from the field path indicated by `field`. Update descriptions and file lists to exclude it. |
| `missing_component` | Add the component to D_dev at the appropriate location. Use `recommended_value` for the new content. |
| `wrong_classification` | Update the description at `field` to `recommended_value`. |

### V2: Evaluation Setting Validity

Finding fields: `setting`, `issue_type`, `description`, `evidence`

V2 operations are structural — they add, remove, merge, or split evaluation settings. The finding's `description` and `evidence` are the primary guide for what to do and how; follow their specifics first. The procedures below are general steps for each operation type — consult them when the finding does not fully specify the implementation details, and read the paper (`preprocessed/text.md`), code (`repositories/`), or existing data (`data/`) to fill in any remaining gaps.

**Quick reference**:

| issue_type | summary |
|------------|---------|
| `should_remove` | Move setting to `rejected_settings[]` |
| `should_merge` | Combine multiple settings into one |
| `should_split` | Split one setting into multiple |
| `missing_setting` | Add a new setting |
| `scope_too_narrow` | Expand a setting's data scope |
| `invalid_eval_method` | Move setting to `rejected_settings[]` (invalid evaluation) |
| `evaluation_alignment_broken` | Move setting to `rejected_settings[]` (data inconsistent with reported scores) |
| `infeasible_eval_mechanism` | Move setting to `rejected_settings[]` (evaluation mechanism not feasible) |

After any V2 structural change, update:
- `final_result.complete_settings_count` and `total_settings_count`
- `data.pattern` if the pattern no longer fits

#### should_remove

Move the named setting from `evaluation_settings[]` to `rejected_settings[]`. Add with fields: `{ "name": <setting name>, "failure_reason": <finding description>, "rejected_at": "verification" }`. Delete the corresponding `data/{setting_dir}/` directory if it exists.

#### invalid_eval_method

Same as `should_remove`, with `failure_reason` describing the invalid evaluation method (e.g., K-fold CV).

#### evaluation_alignment_broken

Same as `should_remove` — move to `rejected_settings[]` with `failure_reason` describing the data inconsistency that breaks evaluation alignment. Delete `data/{setting_dir}/`.

#### infeasible_eval_mechanism

Same as `should_remove` — move to `rejected_settings[]` with `failure_reason` describing the infeasible evaluation mechanism (e.g., depends on Algorithm A's encoder, requires external API). Delete `data/{setting_dir}/`.

#### should_merge

1. **Combine descriptions**: Merge `d_dev` and `d_eval` descriptions from both settings — union of content, deduplicate
2. **Merge data directories**: Move files from one setting's `data/{setting_dir}/` into the other's. Shared files (same content) need not be duplicated
3. **Merge verification blocks**: Combine `separability.dev_eval` and `eval_decomposition` file lists; use the larger `total_size`; keep the more detailed `split_procedure` and `extraction`; reconcile `difficulty` (if they differ, re-assess based on the merged setting's actual separability)
4. **Clean up**: Remove the redundant setting entry from `evaluation_settings[]`; delete its now-empty `data/{setting_dir}/`

#### should_split

1. **Derive sub-settings**: From the finding's `description` + `evidence` and the paper's evaluation structure (results tables, dataset descriptions), determine how many sub-settings to create, their names, and each one's data scope
2. **Create data directories**: Create `data/{sub_setting_dir}/` for each sub-setting
3. **Distribute files**: From the original `data/{setting_dir}/`, copy shared files to each sub-setting directory and move exclusive files to the appropriate one
4. **Construct setting entries**: For each sub-setting, create `name`, `description`, `d_dev` (with `name`, `description`, `source`), `d_eval` (with `name`, `description`, `source`) based on its data scope
5. **Produce verification blocks**: For each sub-setting, generate a complete `verification` block — read paper/code to determine `separability` (`split_procedure`, `extraction`, file lists), assess `difficulty`, calculate `total_size` from the sub-setting's data directory
6. **Clean up**: Remove the original setting entry; delete the original `data/{setting_dir}/` after all files are distributed

#### missing_setting

1. **Identify the setting**: From the finding's `description` + `evidence`, determine the setting name, which dataset it covers, and where it appears in the paper's results
2. **Locate data**: Check if data already exists in `data/` (may overlap with existing settings) or `repositories/` (may contain the dataset)
3. **Acquire if needed**: If data is not already present, download from URLs found in the paper or code, or extract from existing `repositories/`
4. **Organize**: Place files in `data/{setting_dir}/`
5. **Construct setting entry**: Create `name`, `description`, `d_dev` (with `name`, `description`, `source`), `d_eval` (with `name`, `description`, `source`) by reading the paper's data/methods sections
6. **Produce verification block**: Generate a complete `verification` block — `data_path`, `total_size`, `separability` with `difficulty`, `dev_eval`, `eval_decomposition`

#### scope_too_narrow

1. **Identify expanded scope**: From the finding's `description`, determine what data the setting should include but currently doesn't
2. **Update descriptions**: Expand `d_dev` and/or `d_eval` descriptions and source fields to cover the broader scope
3. **Acquire additional files if needed**: Download or extract any files required by the expanded scope; place in `data/{setting_dir}/`
4. **Update verification block**: Add new files to `separability` file lists, recalculate `total_size`, update `sample_count` and `split_procedure`/`extraction` if affected

### V3: Separability Correctness

Finding fields: `field`, `current_value`, `recommended_value`

| issue_type | operation |
|------------|-----------|
| `algorithm_in_split_procedure` | Update `field` to `recommended_value` (remove A's operations from split_procedure). |
| `wrong_feature_scope` | Update `field` to `recommended_value` (expand to full initial-state features). |
| `missing_field_disposition` | Add field disposition analysis at `field` using `recommended_value`. |
| `wrong_sample_count` | Update `field` to `recommended_value`. |
| `parameter_placeholder` | Replace placeholder with the determined value in `recommended_value`. |
| `incorrect_split_specification` | Update the split specification at `field` to `recommended_value` (correct ratio, seed handling, or other split parameters). |
| `difficulty_mismatch` | Update difficulty level at `field` to `recommended_value`. |
| `missing_split_prerequisite` | Insert the prerequisite step into split_procedure at the position indicated by `recommended_value`. |
| `misplaced_eval_operation` | Remove the evaluation-time operation from `field` (split_procedure or y_ref.extraction) and rewrite to `recommended_value`. If the operation was in y_ref.extraction, convert it from an execution step to an informational note. |
| `inference_scoring_mismatch` | Update `field` (sample_count) to `recommended_value` (correct to inference set size). |

### V4: Data Directory Integrity

Finding fields: `file`, `classification`, `recommended_action`

| issue_type | operation |
|------------|-----------|
| `algorithm_artifact` | Delete the file at `data/{file}`. Remove references to this file from `verification.separability` file lists in filter_result.json. Recalculate `verification.total_size`. |
| `irrelevant_file` | Delete the file at `data/{file}`. Recalculate `verification.total_size`. |
| `missing_file` | Acquire the missing file from `repositories/` or download from the setting's source URL. Place it in the correct `data/{setting_dir}/` location. Update `verification.separability` file lists in filter_result.json to include it. |

### V5: Description & Evidence Consistency

Finding fields: `field`, `current_value`, `recommended_value`

| issue_type | operation |
|------------|-----------|
| `algorithm_in_description` | Update `field` to `recommended_value` (remove A contamination from description). |
| `numerical_error` | Update `field` to `recommended_value`. |
| `factual_error` | Update `field` to `recommended_value`. |
| `stale_reference` | Update `field` to `recommended_value` (correct or remove stale reference). |
| `cross_reference_mismatch` | Update `field` to `recommended_value` (align with ground truth). |
