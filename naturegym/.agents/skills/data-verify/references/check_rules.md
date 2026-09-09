# Check Rules: Data Verification (V1–V5)

This document defines the five checks executed by the data-verify skill. Each check produces a `status` (pass/fail/warning) and an array of `findings`.

---

## Terminology Reference

This skill uses the same core definitions as paper-filter and data-check:
- **T = (A, Data, M, S, B)**: The ML task tuple
- **D_dev**: Development data — all prior information available before A starts
- **D_eval = (X_test, Y_ref)**: Evaluation data with input/reference decomposition
- **Algorithm A**: The core algorithm proposed by the paper

### Data Component Classification

| Category | Definition | Belongs to |
|----------|-----------|------------|
| `initial_state` | Raw data that existed before A started | D_dev |
| `data_preparation` | Pre-A operations that transform raw data into the usable dataset. These are not Algorithm A's contribution; they define what the dataset is. | D_dev |
| `algorithm_preprocessing_output` | A's preprocessing outputs (feature selection results, etc.) | Algorithm A — exclude from D_dev |
| `algorithm_output` | A's training products (weights, predictions, logs) | Algorithm A — exclude from D_dev |
| `external_resource` | Resources external to Algorithm A that the method or evaluation depends on (pre-trained models, embeddings, knowledge bases, vocabularies, simulators, oracles, etc.) | D_dev |
| `irrelevant` | Unrelated files (docs, visualization, CI configs) | Neither — exclude from data |

**`data_preparation` vs `algorithm_preprocessing_output`**: Most data_preparation operations are task-defining — they determine the dataset scope or ground truth, rather than being a strategy for solving the task. Key indicators that an operation is data_preparation rather than Algorithm A preprocessing: (1) the paper describes it in the Data/Dataset section as part of dataset construction, not in Methods as part of the proposed approach; (2) all compared models in the paper use the same processed data; (3) without it, the evaluation task cannot be properly defined (e.g., ground truth values or evaluation scope would be indeterminate). Mechanical operations like format conversion and file reorganization are also data_preparation. By contrast, operations where different algorithms may make different choices (e.g., feature selection, data augmentation, algorithm-specific encoding) are `algorithm_preprocessing_output` — the task is still well-defined without them.

**Generic preprocessing note**: Generic preprocessing operations (normalization, missing-value imputation, encoding, etc.) must be distinguished from Algorithm A's specific operations. A's specific operations (e.g., A's own feature selection, A's proposed encoding scheme) must be excluded. Generic preprocessing outputs may be kept or removed depending on the situation, but in either case the description must explain what preprocessing was applied and how it differs from the raw data.

---

## Check V1: D_dev Component Boundary

**Goal**: Verify that D_dev contains only legitimate initial-state components — no Algorithm A outputs or intermediates.

### Procedure

For each `evaluation_settings[]` entry:

1. **Collect declared D_dev components**:
   - Files mentioned in `d_dev.source.instruction`
   - Files listed in `verification.separability.dev_eval.d_dev_files`
   - Resources described in `d_dev.description`

2. **Classify each component** using Phase 2's algorithm boundary analysis (code + paper, equal weight):
   - `initial_state` / `data_preparation` / `external_resource` → **legitimate**
   - `algorithm_preprocessing_output` / `algorithm_output` / `irrelevant` → **should not be in D_dev** → finding: `surplus_component`

3. **Cross-setting dependency verification**: Independently determine whether any declared D_dev pretrained model is actually Algorithm A's training output from another setting in the same paper (pretrain→finetune / transfer learning). Compare the independent determination against what `task_info.data.setting_dependencies` records:
   - Dependency exists per analysis but **absent** from `setting_dependencies` → finding: `missing_cross_setting_dependency` (recommended: add entry to `setting_dependencies`; the model is `algorithm_output` and should not be in D_dev)
   - `setting_dependencies` records a dependency but analysis finds the pretrained model is actually from **external published work** (not Algorithm A in this paper) → finding: `incorrect_cross_setting_dependency` (recommended: remove entry from `setting_dependencies`; the model is a legitimate `external_resource` and should be kept in D_dev)
   - Dependency recorded and confirmed → the pretrained model is `algorithm_output`; if it is still present in the data directory, report `surplus_component` (recommended: delete); if absent, this is expected (do not report `missing_component` — see step 5)
   When a cross-setting dependency is confirmed, the pretrained model is `algorithm_output` — its absence from D_dev is expected and does not produce a `missing_component` finding (see step 5).

4. **Cross-verify with paper**: Check the paper's Data/Methods sections for descriptions of data acquisition and preparation. Verify that what is declared as D_dev matches what the paper describes as available prior to Algorithm A. If the paper describes a component as A's output but filter_result lists it as D_dev (or vice versa), note the discrepancy.

5. **Check for missing components**: Compare Phase 2's identified `initial_state` files against declared D_dev. Any initial-state file required by A but not covered → finding: `missing_component`. **Exception**: pretrained models identified as cross-setting dependencies (step 3) are not missing — the Solver derives them by first solving the source setting.

6. **Check descriptions**: If `d_dev.description` or `d_dev.source.instruction` attributes Algorithm A outputs as properties of D_dev (e.g., "dataset contains A's selected 200 features") → finding: `wrong_classification`. Contextual mentions of A for explanatory purposes (e.g., "this data is subsequently used by A for feature selection") do not constitute wrong classification.

### Status Logic
- **fail**: Any `surplus_component`, `missing_component`, `missing_cross_setting_dependency`, or `incorrect_cross_setting_dependency` found
- **warning**: Only `wrong_classification` (description issues without actual data errors)
- **pass**: No findings

---

## Check V2: Evaluation Setting Validity

**Goal**: Verify that evaluation settings are correctly identified — each is a legitimate (data + evaluation) pair reflecting the paper's main results, and all settings serve one unified task.

### Procedure

#### V2.1: Setting Identification

Review all `evaluation_settings[]` and `rejected_settings[]` against **both the paper and the code** (paper takes precedence when they conflict; see SKILL.md Phase 2):

- **From the paper**: Identify which experiments support the main claims, what datasets are used, how evaluation is structured, and what results are reported (tables, figures).
- **From the code**: Identify which data files are loaded, how train/test splits are performed, and what evaluation scripts exist.
- **Reconcile**: Check that the settings in filter_result.json match what both the paper and code describe.

1. **Should merge?** — Multiple settings that use identical data files AND have the same Y_ref semantic space. The key test: would merging change D_eval's meaning? If Y_ref has the same label space and samples, the settings should be merged (differences are Algorithm A variants). If Y_ref has a different semantic space (e.g., binary vs multi-class classification — different questions being answered), they are legitimately separate. If a single model predicts multiple targets on the same test samples (multi-objective prediction), all targets share one Y_ref semantic space — per-target metrics are evaluation dimensions of one setting, not separate settings.

2. **Should split?** — A single setting that conflates multiple independent evaluations — e.g., treating a shared-training-multiple-testing / leave-one-out cross-dataset experiment as a single setting instead of N. Use the following pattern table (from paper-filter Rule 3.5) to identify settings that should be split:

   | Dataset Pattern | Expected Settings |
   |-----------------|-------------------|
   | Multiple Independent | N Independent Settings: each dataset forms a loop |
   | Shared Training, Multiple Testing | M Independent Settings (Shared D_dev) |
   | Leave-One-Out Cross-Dataset | N Independent Settings: each rotation uses a different dataset as D_eval |
   | Paired Combinations | N Independent Settings: different data combinations form independent loops |

   If a single setting contains sub-tasks with different D_eval (e.g., a leave-one-out experiment treated as one setting instead of N) → finding: `should_split`

   > **K-fold Cross-Validation Exclusion**: K-fold cross-validation on a single dataset does not constitute a valid evaluation setting — D_eval rotates across folds and the reported score is an aggregate → finding: `invalid_eval_method`

3. **Should remove?** — Settings that don't reflect the paper's main claims (auxiliary analysis, ablation studies, sensitivity analysis, toy examples).

4. **Maximum scope** —  Each setting should use the broadest data scope that Algorithm A's variants collectively accessed, not just the subset one specific variant chose to use. This applies when different variants of A use different subsets of the same underlying data source (e.g., one uses a subset of columns while another uses all, or one uses the main file while another additionally uses supplementary files). The setting should include the union of all data accessed by any A variant (the superset). **Notes**: This does NOT mean expanding beyond what the paper's experiments actually used to include external data the authors never accessed/used. If a setting's D_dev or D_eval is unnecessarily narrowed to match A's specific usage → finding: `should_merge` (if multiple settings should be unified) or `scope_too_narrow` (if a single setting's data range needs expansion).

5. **Task unity** — All remaining settings should serve a unified research goal:
   - **Same core algorithm/method** proposed by the paper
   - **Same problem domain** (e.g., all molecular property prediction, all image classification)
   - **Same evaluation paradigm** (e.g., all measure prediction accuracy, all measure generation quality)

   Settings should use the same primary repository/entry scripts and measure the same evaluation paradigm. Metrics may differ by task type (e.g., RMSE for regression, ROC-AUC for classification) as long as they measure the same paradigm.

   If settings test fundamentally different algorithms, solve different problems, or have incompatible evaluation goals → finding: `task_disunity`

#### V2.2: Setting Completeness

Cross-reference the paper's main result tables/figures with the settings list:

1. Extract all datasets/experiments from the paper's main tables and figures where Algorithm A's performance scores are reported
2. For each dataset, check whether it appears in `evaluation_settings[]` or `rejected_settings[]`
3. Any dataset reported in the paper's main results that appears in neither → finding: `missing_setting`

Note: ablation studies, sensitivity analyses, and auxiliary visualizations do not count as main results. Focus on tables/figures that report A's primary performance comparison.

#### V2.3: Evaluation Method Compatibility

For each setting, analyze the paper's evaluation methodology:

1. **K-fold cross-validation** → D_eval does not exist as a fixed concept (evaluation is defined as the aggregate over all folds) → setting is **invalid** → finding: `invalid_eval_method`

2. **Random splits** (multiple seeds and/or ratios) → D_eval exists but parameters need determination → **valid**, parameter correctness checked in V3

3. **Fixed split** (explicit train/test files or indices) → **valid**

#### V2.4: Evaluation Alignment

For each setting, verify that the obtainable data allows meaningful comparison with the paper's reported scores (S/B). Compare the actual data (file counts, schema, distribution) against what the paper describes. If the obtainable data cannot be made consistent with what produced S — due to version differences, unrecoverable subset selection, schema changes, or distribution shifts — finding: `evaluation_alignment_broken` (recommend removal). Exception: papers commonly report approximate numbers (e.g., "~130,000 molecules") — an approximate match is expected and not a discrepancy.

#### V2.5: Evaluation Mechanism Feasibility

For each setting, identify what the evaluation mechanism requires by analyzing the paper's evaluation methodology and the code's evaluation implementation, then check feasibility:

| Evaluation Component Source | Expected Assessment |
|----------------------------|---------------------|
| Static ground truth file (labels, reference values) | Feasible |
| Official/public library (e.g., RDKit, FEniCS) | Feasible (dependency noted) |
| Public pre-trained model independent of A | Feasible (included as external_resource) |
| Simulator/binary in repository | Feasible only if exists and executable |
| Algorithm A's own component used for scoring (e.g., A's encoder, A's discriminator) | **Not feasible** — leaks method information |
| External service/API with no local alternative | **Not feasible** — cannot guarantee reproducibility |

If a setting's evaluation mechanism is infeasible but was not rejected → finding: `infeasible_eval_mechanism` (recommend removal), with evidence explaining why the mechanism is infeasible.

### Status Logic
- **fail**: Any `should_merge`, `should_split`, `should_remove`, `scope_too_narrow`, `invalid_eval_method`, `missing_setting`, `evaluation_alignment_broken`, or `infeasible_eval_mechanism`
- **warning**: Minor concerns about task unity
- **pass**: Settings correctly identified

---

## Check V3: Separability Correctness

**Goal**: Verify that separability descriptions (split_procedure, eval_decomposition) correctly reflect the data's initial state without Algorithm A contamination (per the Core Principle above).

**Scope principle**: Before finalizing any V3 finding, verify the recommended_value places the operation at the correct scope for its type. In particular, if a recommendation introduces or makes explicit a data_preparation operation in one field, check whether it should also be reflected on the other side of the D_dev/D_eval boundary — a data_preparation operation that the Solver must know about during training should not end up described only on the D_eval side.

### Procedure

#### V3.1: split_procedure Scope

For each setting's `verification.separability.dev_eval.split_procedure`:

1. **Identify each step** in the procedure
2. **Classify each step**:
   - Sample-level splitting operations (train_test_split, index selection) → **legitimate**
   - `data_preparation` operations that the split depends on (see `data_preparation` vs `algorithm_preprocessing_output` in Terminology for how to distinguish) → **legitimate** (should be annotated as applying to both D_dev and D_eval when the paper applies them uniformly across whole dataset)
   - Algorithm A operations (feature selection, feature engineering, data augmentation, encoding that doesn't change label space) → **should not be here** → finding: `algorithm_in_split_procedure`
   - Evaluation-time operations (operations executed only after the Solver produces output, before metric computation — such as scoring-time sample filtering, output-to-reference alignment, or post-prediction transforms that the Solver does not need to be aware of during training). Key distinction from data_preparation: evaluation-time operations do NOT affect the training data — the Solver trains without knowledge of them. If the operation must be applied to training data for the Solver to work correctly (e.g., target-space transforms like log scaling that all methods train on), it is data_preparation, not evaluation-time. → **should not be here** → finding: `misplaced_eval_operation`
3. **Check for missing data_preparation prerequisites**: Cross-reference the paper and code to identify `data_preparation` steps that the split depends on (e.g., class balancing that must occur before train/test split). If such a step is required for the split to be correctly executed but is absent from split_procedure → finding: `missing_split_prerequisite`

   **Note**: Operations that are executed only after the Solver produces output (before metric computation) are not split prerequisites — they belong to the evaluator's internal logic. Distinguishing criterion: the Solver does not need to know about the operation during training. If the operation must be applied to training data for the Solver to work correctly (e.g., target-space transforms like log scaling), it is data_preparation, not evaluation-time — even if all methods share it.

4. **D_dev internal structure**: If the paper and code distinguish training and validation subsets within D_dev (e.g., separate files, explicit index ranges, or split ratios), verify that split_procedure includes instructions for this separation. If the author's train/val distinction is evident but absent from split_procedure → finding: `missing_split_prerequisite`

#### V3.2: eval_decomposition Scope

For each setting's `verification.separability.eval_decomposition`:

1. **X_test scope**: Should include all input features available in the initial state — not just the subset A chose to use. If X_test references only Algorithm A-selected features → finding: `wrong_feature_scope`

2. **Y_ref completeness**: Should contain all information needed for metric computation

3. **Field disposition analysis**: When the source data has fields beyond X_test and Y_ref, each extra field should be classified as:
   - `y_ref-component`: Required for metric computation → retain in Y_ref
   - `y_ref-leaking`: Would reveal Y_ref information but is not needed for metric computation → discard from both X_test and Y_ref
   - `auxiliary`: Independent of Y_ref → preserve in X_test

   If this analysis is absent → finding: `missing_field_disposition`

4. **ID-field alignment**: If the data has identifier fields, they should be retained in both X_test and Y_ref

5. **Inference set vs scoring set**: The data the model does inference on (X_test) and the data that ultimately enters scoring may differ — the evaluation code may filter samples or align outputs before computing the metric. Check for two issues:
   - `y_ref.extraction` should only describe how to prepare the Y_ref **file** from source data. If it includes evaluation-time operations (steps executed only after the Solver produces output, that the Solver does not need to know about during training — see V3.1 Step 2 for the distinction from data_preparation) presented as extraction steps → finding: `misplaced_eval_operation`. Such operations may be mentioned as informational notes, but must not be presented as file preparation steps.
   - When the evaluation code reduces the scored sample set relative to the full X_test (e.g., filtering by annotation count, excluding samples that fail quality checks), `x_test.sample_count` should reflect the **inference set** (all samples the Solver must predict on), not the scoring subset. If `sample_count` uses the scoring subset size instead → finding: `inference_scoring_mismatch`

6. **Operation scope**: For any operation identified or proposed in V3.2 findings, classify it (data_preparation / evaluation-time / Algorithm A per Terminology and V3.1 Step 2) and verify the finding places it at the appropriate scope. For example: a data_preparation operation found in extraction should also be reflected in D_dev if the Solver needs it during training; an evaluation-time operation should not be proposed as a data file preparation step; removing an Algorithm A operation from extraction should not leave it referenced in D_dev descriptions.

#### V3.3: Sample Count

1. Determine the expected test set size from `split_procedure` parameters (e.g., split ratio × total samples, index range length, held-out dataset size)
2. **Cross-validate independently**: Also determine the expected test set size from the paper's reported results (tables, text mentioning test set size or number of test samples) and the code's evaluation logic (e.g., hardcoded constants like `NUM_SAMPLES`, assertion checks, or loop bounds in evaluation scripts). If the procedure-derived count differs from the paper/code-derived count, this indicates the split_procedure may be incomplete — report finding: `wrong_sample_count` (and investigate whether `missing_split_prerequisite` applies in V3.1)
3. Compare with recorded `x_test.sample_count` and `y_ref.sample_count`. Any mismatch with either the procedure-derived or independently-derived expected count → finding: `wrong_sample_count`. Common error patterns include: count equals total dataset size instead of test set size, ratio calculation errors, x_test and y_ref counts not matching, or null/missing values where a count is determinable
4. For settings with multiple sub-tasks (e.g., leave-one-out), sample counts vary per sub-task — the recorded value should list per-sub-task counts or a representative range

#### V3.4: Split Specification Completeness

Verify that split_procedure fully specifies all parameters needed to reproduce the split. Check by split type:

1. **Random split**: Cross-reference the paper and code to determine the split ratio and seed.
   - **Ratio**: If the paper reports scores at a specific ratio and the code confirms it, that ratio should appear as a determined value — not as "e.g." → finding: `parameter_placeholder`
   - **Seed**: Code has a single fixed seed → use it; code has multiple seeds → pick one and record it; author does not fix a seed → split_procedure should not fix one either
   - Placeholder text ("e.g.", "pick one") for a determinable parameter → finding: `parameter_placeholder`
   - **Content consistency**: After determining the correct parameter handling above, verify split_procedure text actually reflects it. Common errors:
     - Author doesn't fix seed, but split_procedure says "set a seed" or implies a specific seed is needed → finding: `incorrect_split_specification`
     - Code has a fixed seed, but split_procedure omits it or says "pick any seed" → finding: `incorrect_split_specification`
     - Ratio is determined, but split_procedure states a different ratio → finding: `incorrect_split_specification`

2. **Fixed split** (index file / pre-defined split): Verify the index file or split definition is correctly referenced, the file exists in the data directory, and the format is described clearly enough to execute.

3. **Cross-dataset split** (leave-one-out, paired combinations): Verify the dataset assignment scheme is complete — which datasets serve as D_dev and D_eval in each sub-task must be unambiguous.

4. **Temporal / domain split**: Verify the cutoff point or domain selection criteria is explicitly stated and deterministic.

#### V3.5: Difficulty Level

Based on the analysis performed in V3.1–V3.4, independently assess the difficulty of each setting and compare with data-check's assessment.

**Step 1: Independent assessment** — For each setting, determine what `dev_eval` and `eval_decomposition` difficulty levels should be by applying the difficulty scale (from data-check Check 4.3) to the actual split mechanism and decomposition analyzed in V3.1–V3.4:

| Level | Name | Criteria |
|-------|------|----------|
| 1 | `trivial` | **Physically separate**: Components already in distinct files/directories |
| 2 | `simple` | **Explicitly marked**: Share a file, but boundaries defined by inherent structure (column, key) |
| 3 | `moderate` | **Indirectly defined**: Fully determined but requires cross-referencing, executing a straightforward algorithm, or running a clean script |
| 4 | `complex` | **Programmatically bound**: Requires adapting scripts, non-trivial domain algorithms, or domain-specific format parsing |
| 5 | `ambiguous` | **Under-specified**: Partially known but not uniquely determined — missing parameters, multiple valid decompositions, or coupled logic |
| 6 | `infeasible` | **Missing information**: Essential boundary information fundamentally absent; OR **Paper-repository inconsistency**: Paper description contradicts repo files/code, cannot objectively determine true boundaries |
| — | `not_applicable` | Separation does not apply |

Apply the scale based on the **verified** state of split_procedure and eval_decomposition (i.e., after accounting for any V3.1–V3.4 findings that would change the procedure if corrected).

**Step 2: Seed-only ambiguity rule** — When assessing `dev_eval`, the absence of a random seed alone does **not** constitute under-specification if the author genuinely does not fix a seed (per V3.4: "Author does not fix a seed → split_procedure should not fix one either"). In such cases, the split procedure is fully determined (execute with any seed), and the difficulty should reflect the actual mechanism complexity (typically `moderate`), not `ambiguous`.

**Step 3: Compare and report**

1. Compare the independently assessed `dev_eval` and `eval_decomposition` levels with data-check's recorded values
2. If they differ → finding: `difficulty_mismatch` (with `current_value` = data-check's level, `recommended_value` = independently assessed level, and evidence explaining why)
3. Check that `overall` is consistent with the two sub-dimensions and `difficulty_reason` explains the rationale. Internal inconsistency → finding: `difficulty_mismatch`

### Status Logic
- **fail**: Any `algorithm_in_split_procedure`, `wrong_feature_scope`, `wrong_sample_count`, `missing_split_prerequisite`, `incorrect_split_specification`, `misplaced_eval_operation` (when causing incorrect execution), or `inference_scoring_mismatch`
- **warning**: `missing_field_disposition`, `parameter_placeholder`, `difficulty_mismatch`, or `misplaced_eval_operation` (purely descriptive)
- **pass**: No findings

---

## Check V4: Data Directory Integrity

**Goal**: Verify that `data/{setting_dir}/` contains only initial-state (D_dev) and evaluation-target (D_eval) files — no algorithm artifacts.

### Procedure

For each setting that has a `verification.data_path`:

1. **List all files** in `data/{setting_dir}/` recursively
2. **Classify each file** using Phase 2's algorithm boundary analysis
3. Flag issues:
   - `algorithm_preprocessing_output` / `algorithm_output` → finding: `algorithm_artifact` (recommended action: delete)
   - `irrelevant` → finding: `irrelevant_file` (recommended action: delete)
   - Expected `initial_state` file missing → finding: `missing_file` (recommended action: add). **Exception**: for dependent settings in `setting_dependencies`, the pretrained model from the source setting is `algorithm_output` and its absence is expected — do not flag as `missing_file`.

### Status Logic
- **fail**: Any `algorithm_artifact` or `missing_file`
- **warning**: Only `irrelevant_file`
- **pass**: Directory contains exactly the expected data files

---

## Check V5: Description & Evidence Consistency

**Goal**: Verify that descriptions and evidence in filter_result.json accurately reflect the actual data.

### Procedure

#### V5.1: Description Fields

Check all description fields in `task_info.data` for Algorithm A contamination and accuracy:

1. **Fields to check**: `evaluation_settings[].description`, `d_dev.description`, `d_dev.source.instruction`, `d_eval` descriptions, and `verification.separability` descriptive fields (split_procedure, extraction, etc.)
2. **Algorithm A contamination**: Any field that attributes Algorithm A outputs as properties of the data (e.g., "features reduced to N via [A's method]", "after [A's preprocessing]", or instructions that include A's operations as steps) → finding: `algorithm_in_description`
3. **Accuracy**: Descriptions should match the actual data content

#### V5.2: Evidence-Informed Task Info Verification

Use factual claims in Level 3 and Level 4 evidence as cross-check signals for task_info accuracy. Evidence fields are process records of progressive filtering — errors in evidence that were corrected in later levels are expected and do not need fixing.

1. **Spot-check evidence claims**: Independently verify key factual claims in Level 3/4 evidence by reading actual files — row counts (`wc -l` or Python), column counts (parse header), dataset versions, feature types, file format descriptions, class distributions, etc.
2. **Trace confirmed errors to task_info**: When a claim is genuinely incorrect (not an approximation), check whether the same error propagated to task_info fields (descriptions, separability details, sample counts, etc.):
   - task_info is also wrong → finding: `numerical_error` or `factual_error`, with `field` pointing to the affected **task_info** field, and your judgment of the root cause
   - task_info is correct → no finding (evidence-only errors are acceptable as part of the progressive filtering record)

#### V5.3: Cross-Reference Consistency

1. **task_info.data ↔ Level 3/4**: Check that `evaluation_settings[]` and `rejected_settings[]` in task_info are consistent with the corresponding Level 3 Rule 3.5 and Level 4 Check 4.5 results. Level 3 and Level 4 are progressive stages — Level 3 may contain errors that Level 4 subsequently corrected (via task_info_corrections). When task_info diverges from Level 3 evidence but agrees with Level 4, this is expected and not a finding. The priority is task_info accuracy, as task-build uses task_info downstream.

2. **Descriptions ↔ Verification**: Check that `d_dev.description` / `d_eval.description` are consistent with `verification.separability` details

3. **Stale references in task_info**: Check that task_info fields (e.g., `d_dev.source.instruction`, descriptions) do not reference files that do not exist or have been removed. Stale references that only appear in Level 3/4 evidence but not in task_info are not reported — evidence is a process record.

Any task_info inconsistency → finding: `cross_reference_mismatch`; stale reference in task_info → finding: `stale_reference`

#### V5.4: Size Estimation Validation

Compare the actual total data size (from `verification.total_size_bytes` across all settings) against the estimated size from `filter_result.json` Rule 3.6 (`estimated_total_bytes`):

1. Compute actual total: sum of `verification.total_size_bytes` across all completed evaluation settings
2. Read estimated total from `filtering_process[2].rules` → Rule 3.6 → `estimated_total_bytes`
3. If estimated is null/absent (legacy filter_result without Rule 3.6) → skip this check
4. Compare: if actual differs from estimated by more than **2x** in either direction → finding: `size_estimation_deviation`
   - Record both actual and estimated values in the finding
   - This is informational — helps calibrate the estimation pipeline
5. If actual total moves the paper to a different tier than estimated (e.g., estimated S but actual M) → finding: `size_tier_mismatch`

### Status Logic
- **fail**: Any `numerical_error` or `factual_error` in task_info with >10% deviation or material impact, or `cross_reference_mismatch` affecting task_info correctness
- **warning**: Minor `numerical_error`, `algorithm_in_description`, `stale_reference`, `size_estimation_deviation`, or `size_tier_mismatch`
- **pass**: No findings
