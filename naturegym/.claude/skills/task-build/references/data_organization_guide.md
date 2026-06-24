# Phase 0: Data Organization Guide

## Objective

Transform the raw data from data-check output (`data/{setting_dir}/`) into the standardized task package structure: solver-visible data in `problem/data/{setting}/` and ground truth in `evaluation/ground_truth/{setting}/`.

## Step 0.1: Build Plan

From the context established in Prerequisites, focus on the data-organization-specific fields:

1. **Passing settings**: `task_info.data.evaluation_settings[]` entries
2. **Separability info**: Each setting's `verification.separability` block:
   - `difficulty` — the split difficulty level
   - `dev_eval` — how to separate d_dev and d_eval
   - `eval_decomposition` — how to extract X_test and Y_ref
3. **Data paths**: Each setting's `verification.data_path`

## Step 0.2: Setting Merge/Split Check

Verify the setting structure from filter_result.json is correct. In most cases paper-filter has already 
identified settings properly; this is a **sanity check** focused on issues that become visible when working with the physical data.

### Merging Rule
Settings are distinguished solely by their data components (D_dev and D_eval). If two settings share **identical data files**, they must be merged into a single setting — even if the paper reports them separately due to different algorithmic configurations. The task environment contains all data; the algorithm decides what to use.

**How to check**: Compare the `d_dev` and `d_eval` data sources across all passing settings. If two settings reference the same files/directories, merge them.

### Splitting Rule
A single setting may actually represent multiple evaluation instances if it contains multiple independent test sets with separately reported scores (e.g., shared training with multiple testing targets, or leave-one-out cross-dataset evaluation where each dataset takes turns as test set).

**How to check**: Compare the setting description against the paper's experimental setup and score reporting. If separate scores are reported for identifiable sub-tasks within one setting, split into separate instances.

## Step 0.3: Data Completeness Check

For each setting, verify that `data/{setting_dir}/` contains everything needed:

1. **Cross-check against filter_result.json**: Compare actual files against all `d_dev` and `d_eval` components. Also verify whether filter_result.json itself has gaps. (possible if it wasn't detected during the preceding step, or was detected but not actually downloaded)
2. **Missing data**: If absent, download based on `source` in filter_result.json; if filter_result.json lacks the component, identify the source from the paper/repository and acquire it.
3. **Shared data**: Verify each setting is self-contained — if any shared component is missing, copy from another setting or re-download.
4. **Unresolved archives**: Decompress any unexpanded archives (may reveal files that affect the split plan). Delete originals after extraction.

### Setting Degradation

If a setting's data is incomplete and cannot be remediated (component unavailable, download fails, etc.):
- **Do NOT process** this setting in subsequent steps — leave its `data/{setting_dir}/` untouched
- Record the failure in `task_build.phase_0.dropped_settings`
- All downstream phases (data_description, README, evaluator, metadata) must exclude dropped settings
- **Cascade drop**: When `task_info.data.setting_dependencies` exists, if a source setting is dropped, all its dependent settings must also be dropped
- If **all** settings are dropped, set `status` to `failed` and terminate the build early

## Step 0.4: Data Cleanup

For each setting's data directory (`data/{setting_dir}/`), apply a **Whitelist Approach**: the data directory must ONLY contain the Initial State (D_dev) and the Evaluation Target (D_eval).

**NOTE**: Use the D_dev and D_eval component lists in filter_result.json as the whitelist reference. If a file's role is unclear or potentially misclassified in filter_result.json, consult the paper and repository context to verify.

**NOTE**: Only clean `data/` directories. Do NOT touch `repositories/` (reference only, not part of final package).

**NOTE**: When `task_info.data.setting_dependencies` exists, pretrained model files produced by a source setting's Algorithm A training are `algorithm_output` — they must be removed from the dependent setting's data directory.

### Files to KEEP (Whitelist)
- **D_dev components**: Training data, validation data, pre-trained model weights (external dependencies, not algorithm A outputs), vocabulary/ontology/knowledge base files, configuration files needed for data interpretation, environment simulators, parameter files
- **D_eval components**: Test input files (X_test sources), ground truth / reference files (Y_ref sources) — Y_ref will be moved to `evaluation/ground_truth/` during the split step
- **Splitting metadata**: Index files, ID lists, split definition files needed for the split step

### Files to REMOVE (everything not on the whitelist)
- **Algorithm artifacts**: Model checkpoints (`.ckpt`, `.pth`, `.pt`), training logs, intermediate predictions, generated features, cached computations — anything produced *by or during* running algorithm A (outputs or intermediate products of Algorithm A itself)
- **Experiment outputs**: `predictions.*`, `results.*`, `scores.*`, `figures/`, `plots/`, generated images
- **Logs & caches**: `*.log`, `tensorboard/`, `wandb/`, `__pycache__/`, `*.pyc`, `.cache/`
- **Residual archives**: Archives that have been fully extracted but not yet deleted
- **Documentation**: READMEs, license files from the original repo that ended up in data/
- **System files**: `.DS_Store`, `.git/`, `.gitignore`

## Step 0.5: Data Split and Reorganization

For each passing setting (excluding dropped settings), use the `verification.separability` information to split and reorganize.

Drop a setting and record in `task_build.phase_0.dropped_settings` when:
- The split **cannot be determined**: insufficient information to know what the split should be (e.g., paper describes a dataset size that conflicts with the repository files with no explanation, no config file exists for the setting)
- The split **cannot be executed**: required data is missing, scripts fail, or instructions are contradictory

If all settings are dropped, set `status` to `failed` and terminate early.

### General Principles

1. **Always follow split_procedure and extraction**: The `split_procedure` (for dev_eval) and `extraction` (for x_test/y_ref) fields in filter_result.json contain step-by-step instructions produced by data-check. These are the primary guide for every difficulty level.
2. **Fallback rules**: When filter_result.json instructions do not explicitly address the following aspects, apply these defaults:
   - **Scope**: Only perform sample-level splitting. Do NOT perform feature engineering, data augmentation, or other algorithm-specific preprocessing. Also do NOT include evaluation-time operations (operations executed only after the Solver produces output, before metric computation — such as scoring-time sample filtering or output-to-reference alignment).
   - **Data preparation in split**: The split may depend on data_preparation operations (Pre-A operations that transform raw data into the usable dataset. These are not Algorithm A's contribution; they define what the dataset is). These should be described in split_procedure.
   - **Randomness handling**: Do NOT drop a setting merely because the split involves randomness without a fixed seed — execute it following the author's protocol and document the non-determinism. If the author does not fix the seed, do not fix it yourself. If the author provides multiple random split configurations (multiple seeds or ratios), choose one and document the choice.
   - **Information preservation**: Classify additional fields as *y_ref-component* (needed for metric computation → retain in Y_ref), *y_ref-leaking* (reveals Y_ref but not needed for metrics → discard), or *auxiliary* (independent of Y_ref → preserve in X_test).
   - **ID-field alignment**: If the source data contains an identifier field, retain it in **both** X_test and Y_ref for downstream alignment.
   - **Output format**: Default to the same format as the source file. Only convert when the original format cannot be preserved.
   - **D_dev internal structure**: Follow the train/val distinction within D_dev. If no such distinction is evident, keep D_dev as a single block.


### Target Structure
```
problem/data/{instance}/
├── [d_dev files]        # Training data, validation data, dependencies
└── [x_test files]       # Test inputs (what the solver receives)

evaluation/ground_truth/{instance}/
└── [y_ref files]        # Reference answers (hidden from solver)
```

### Instance Naming

Instance folder names in `problem/data/` and `evaluation/ground_truth/` must be identical. Use short, descriptive, lowercase names with underscores:
- Remove task-type suffixes from `data/` directory names (e.g., `bbbp_classification` → `bbbp`)
- Remove verbose descriptors (e.g., `hpbmc_shuffle_split_cross_validation` → `hpbmc_shuffle_split`)
- When splitting one setting into multiple instances, name each by its distinguishing characteristic (e.g., `pancreas_cross_dataset_experiment` → `pancreas_baron`, `pancreas_muraro`, ...)
- Avoid paper-specific or algorithm-specific terms in names

### Y_ref Type and File Placement

How Y_ref files are placed depends on the Y_ref type:

| Y_ref Type | problem/data/{setting}/ | evaluation/ground_truth/{setting}/ |
|------------|------------------------|------------------------------------|
| **Label** (static ground truth: labels, scores, structures) | D_dev + X_test only | Y_ref label files |
| **Oracle** (deterministic scoring function / simulator) | D_dev + X_test + Oracle (if solver needs it) | Oracle Copy (evaluator needs it for scoring) |
| **Distribution** (target distribution / quality reference) | D_dev + X_test + Oracle if Solver needs it | Reference sample set, statistics, and/or Oracle Copy for quality evaluation |

> **Note on oracle extraction**: In data-check, oracle files are classified as `external_resource` as part of D_dev. During task-build reorganization, identify the oracle files, and place them according to the table above.

### Evaluation Component Handling

This section covers **both** the oracle itself (which IS the y_ref for Oracle-type tasks, and may also serve as the y_ref component for Distribution-type tasks) **and** auxiliary computational dependencies needed to run evaluation for any y_ref type.

**Source acceptability**:

| Source | Action | Rationale |
|--------|--------|-----------|
| **Official library** (e.g., RDKit, FEniCS) | Use directly; add library to Dockerfile.v3 | Reproducible, well-maintained |
| **Official benchmark evaluation component** (e.g., competition scorer, dataset-provided eval code) | Use directly or adapt interface to fit task package format; **preserve original scoring logic faithfully**. | Community standard, no IP concern, preserves comparability |
| **Public pre-trained model** (independent of algorithm A) | Include model weights | Decoupled from the paper's method |
| **Author-implemented function** | Re-implement by referencing original code | The author's code is typically already in `data/` (placed by data-check as `external_resource`) or findable in `repositories/`. Avoid directly copying author code (IP) |
| **External service/API** (no local installable version) | **Not suitable** — drop affected settings (Step 0.3 degradation) | Cannot guarantee reproducibility |
| **Part of algorithm A** (e.g., algorithm A's encoder used for scoring) | **Not suitable** — drop affected settings (Step 0.3 degradation) | Leaks method information; forces agent to use algorithm A components |
| **Complex simulator/binary** | Case-by-case; suitable only if installable and scriptable | Must be automatable in Docker |

**File placement**:
- Solver also needs the component (e.g., Oracle for optimization) → place in both `problem/data/{setting}/` and `evaluation/`(`ground_truth/{setting}/` for per-instance, `shared/` for cross-instance)
- Only evaluator needs it → place in `evaluation/` only
- Auxiliary files (vocabulary, lookup tables) follow the same placement as their parent component
- For components that require re-implementation (author-implemented sources), the re-implemented scoring code is placed either as a standalone script alongside evaluator.py, or inlined directly into evaluator.py.
- Binary data files the scoring depends on (model weights, lookup tables, etc.) are placed as-is — no re-implementation needed for non-code files.
- filter_result.json's "preserved as-is" refers to data acquisition integrity (files were downloaded without modification), not to task-build packaging. Re-implementation during packaging is expected and required.

**Script cleaning checklist**: After placing any `.py` script into the task package — whether re-implemented (author-implemented functions), used directly (benchmark evaluation scripts), or included as-is (simulators) — apply the following checks **in order** before proceeding:

1. **Remove irrelevant content**: Delete useless, unused, or completely unrelated parts (e.g., dead code, unused functions, plotting logic).
2. **Remove harmful content**: Strip out any code involving Algorithm A's targets, algorithmic design, training logic, or methodology. This includes functions that implement or reference the paper's proposed method. Maintain the information firewall.
3. **Ensure usability**:
   - File paths must be relative to the task package structure — replace any hardcoded paths from the original repository layout
   - Fix deprecated API calls and library compatibility issues (version-specific calls, removed functions, etc.) — refer to [references/Dockerfile.base.v3](Dockerfile.base.v3) for the pre-installed library versions in the target environment
   - Verify no syntax errors: `python -m py_compile <script.py>`
   - Verify imports are resolvable in the task's target environment

## Step 0.6: Verification and Record

After reorganization:
1. Verify `problem/data/{setting}/` contains all solver-visible files (d_dev + x_test)
2. Verify `evaluation/ground_truth/{setting}/` contains y_ref files
3. Verify no y_ref information leaked into `problem/data/`
4. Verify sample counts match between x_test and y_ref
5. Verify all files are readable (quick sanity check)
6. Record Phase 0 actions in `task_build.phase_0`
