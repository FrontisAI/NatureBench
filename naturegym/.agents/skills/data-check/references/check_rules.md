# Deep Verification Rules (Level 4)

Level 4 performs **actual data verification**, upgrading paper-filter's Level 3 lightweight checks. Every check here operates on downloaded files rather than HTTP status codes or README inspection.

## Output Format

All checks produce a uniform output recorded in `filtering_process[3].rules[]`:

```json
{
  "rule_id": "4.x",
  "rule_name": "string",
  "passed": "boolean",
  "reason": "string (concise pass/fail explanation)",
  "evidence": "string (key facts: file paths, sizes, sample counts, error messages)"
}
```

Exception: Check 4.5 adds a `"unified": boolean` field alongside the standard fields — see [output_schema.md](output_schema.md).

Exception: Task information corrections are applied in place to `task_info` in filter_result.json and logged to `data_check_corrections.txt` — see [output_schema.md](output_schema.md).

Structured verification data is recorded once per setting in `evaluation_settings[].verification` — see [output_schema.md](output_schema.md). The checks here produce **decision summaries only**; they do not duplicate the structured data.

---

## Maximum Scope Principle

Each setting should use the broadest data scope that Algorithm A's variants collectively accessed, not just the subset one specific variant chose to use. When different variants of A use different subsets of the same underlying data source (e.g., one uses a subset of columns while another uses all, or one uses the main file while another additionally uses supplementary files), they should be treated as a single evaluation setting whose data scope is the union (superset) of all data accessed by any A variant. **Notes**: This does NOT mean expanding beyond what the paper's experiments actually used to include external data the authors never accessed/used.

---

## Data Component Classification

This section defines the classification used in Phase 4 (Algorithm A Boundary Analysis) and referenced by Phase 6 (Cleanup).

### Classification Table

| Category | Definition | Disposition |
|----------|-----------|-------------|
| `initial_state` | Raw data that existed before A started | Keep in D_dev |
| `data_preparation` | Pre-A operations that transform raw data into the usable dataset; they define what the dataset is, not a strategy for solving the task | Keep in D_dev |
| `algorithm_preprocessing_output` | A's preprocessing outputs (e.g., A's selected feature lists) | Exclude — mark for cleanup |
| `algorithm_output` | A's training products (weights, predictions, logs) | Exclude — mark for cleanup |
| `external_resource` | External resources from other work that A depends on (pre-trained models, embeddings, knowledge bases, vocabularies, etc.) | Keep in D_dev |
| `irrelevant` | Unrelated files (docs, visualization scripts) | Exclude — mark for cleanup |

#### Cross-Setting Pretrained Models

When Phase 4 analysis reveals that a dependent setting's D_dev pretrained model is actually Algorithm A's training output from another setting in the same paper (pretrain→finetune / transfer learning), classify the model as `algorithm_output` (exclude from data directory), but this does NOT cause the dependent setting to fail Initial State checks — the Solver is expected to derive it by first solving the source setting.

**Detection**: Trace model loading paths in code; identify when a dependent setting loads checkpoint/weights produced by another setting's training process.

**When discovered (bidirectional)**:
- **Cross-setting dependency found but not recorded**: Phase 4 confirms the model is Algorithm A's output from another setting in this paper, but `setting_dependencies` is absent or incomplete → add/update `setting_dependencies`, update dependent setting's `d_dev.description`
- **Recorded dependency contradicted by evidence**: `setting_dependencies` records a cross-setting dependency, but code analysis shows the model actually comes from external published work (e.g., loaded from a public checkpoint URL, different repository, or pre-existing model not trained by this paper's code) → remove the incorrect entry from `setting_dependencies` and reclassify the model as `external_resource` in `d_dev`

In both cases, log the finding in `data_check_corrections.txt` with concrete evidence (model loading path, training script, or URL).

#### `data_preparation` vs `algorithm_preprocessing_output`

data_preparation operations are task-defining — they determine the dataset scope or ground truth. Key indicators: (1) the paper describes it in the Data/Dataset section, not in Methods; (2) all compared models use the same processed data; (3) without it, the evaluation task cannot be properly defined. Mechanical operations (format conversion, file reorganization) are also data_preparation. By contrast, operations where different algorithms may make different choices (feature selection, data augmentation, algorithm-specific encoding) are `algorithm_preprocessing_output` — the task is still well-defined without them.

When both raw data and data_preparation output are available, prefer the data_preparation output (it is the actual dataset all methods used; reproducing it from raw data risks inconsistency). In either case, the description must explain what preprocessing was applied.

#### Generic Preprocessing

Generic operations (normalization, missing-value imputation, etc.) must be distinguished from A's specific operations. A's specific operations (A's own feature selection, A's proposed encoding) must be excluded. Generic preprocessing outputs may be kept or removed, but the description must explain what was applied.

### Analysis Procedure

1. **Locate data-loading code** — search for data loaders (`dataset.py`, `dataloader.py`, `data.py`), entry points (`train.py`, `main.py`, `run.py`), configs (`config.yaml`, `args.py`), preprocessing scripts (`preprocess.py`, `prepare_data.py`), and README setup instructions. Grep for I/O patterns (`pd.read_`, `np.load`, `h5py.File`, `torch.load`, `open(`, `load_dataset(`) and path construction (`data_dir`, `data_path`). Focus on the main experiment code path.
2. **Triangulate from three sources** (paper takes precedence when they conflict):
   - **Paper**: Read Methods/Data sections to understand what A is, what data it uses, and how data was collected/prepared
   - **Code**: Analyze processing pipeline to identify operations and file I/O patterns
   - **Data files**: Inspect actual downloaded files with their formats, sizes, and content
3. **Classify each data-related file** using the table above.
4. **Reconcile with task_info**: Match classification results against `d_dev`/`d_eval` in each setting; correct missing components, mismatches, and wrongly included Algorithm A outputs. Record corrections in `data_check_corrections.txt` with evidence.

### Evaluation Mechanism Feasibility

Identify what each setting's evaluation mechanism requires (static ground truth, scorer, oracle, simulator, distributional reference). Check whether the mechanism is feasible:

| Evaluation Component Source | Feasibility | Action |
|----------------------------|-------------|--------|
| Static ground truth file (labels, reference values) | Feasible | Normal Y_ref handling |
| Official/public library (e.g., RDKit, FEniCS) | Feasible | Note dependency |
| Public pre-trained model independent of A | Feasible | Include as external_resource |
| Simulator/binary in repository | Check existence and executability | If exists and runs → feasible; otherwise → reject setting |
| Algorithm A's own component used for scoring (e.g., A's encoder, A's discriminator) | **Not feasible** | Reject setting — leaks method information |
| External service/API with no local alternative | **Not feasible** | Reject setting — cannot guarantee reproducibility |

Settings rejected for evaluation mechanism infeasibility are moved to `rejected_settings[]` with reason documenting the specific issue.

---

## Check 4.1: Data Acquisition Verification

**Corresponding Level 3 rule**: Rule 3.1 (Zero-Interaction Acquisition)

**Level 3 did**: Verified data can be acquired without manual interaction — checked URL accessibility, confirmed no authentication/NDA/institutional access required

**Level 4 does**: Verify files have been successfully downloaded to local disk, have plausible sizes, and are readable.

### Criteria

For each data component (d_dev, d_eval) of each evaluation setting:

1. **File exists and non-trivial**: File exists at the expected local path, is non-empty (size > 0 bytes), and has a plausible size for its role. Files that are suspiciously small for their expected content (e.g., < 1 KB for a dataset file) should be treated as acquisition failures (likely error pages or corrupted downloads).
2. **File readability**: Use `inspect_data.py` to verify all data files are readable. For files with unsupported formats, attempt alternative verification methods (basic file opening, header inspection). Files that cannot be verified as readable by any method cause the setting to fail.

### Pass condition
Per-setting: all data files for that setting exist, have plausible sizes, and are readable. Overall: at least one setting passes.

### Informational: Size Estimate Comparison

After computing `total_size_bytes` for each setting, compare against the estimated size from `filter_result.json` Rule 3.6 (`estimated_total_bytes`) if available:

- If `total_size_bytes` > 2x `estimated_total_bytes`, or `estimated_total_bytes` > 2x `total_size_bytes`, record the discrepancy in the Check 4.1 `evidence` string (e.g., "Size discrepancy: actual 4.2 GB vs estimated 1.1 GB (3.8x)")
- This is **informational only** — it does NOT affect the pass/fail outcome of Check 4.1
- The comparison helps downstream analysis identify papers where size estimates were significantly off

---

## Check 4.2: Initial State Integrity Verification

**Corresponding Level 3 rule**: Rule 3.2 (Initial State Completeness)

**Level 3 did**: Verified D_dev components are obtainable based on documentation review and link checks

**Level 4 does**: Verify D_dev components are present and accessible in the downloaded files

### Criteria

1. **D_dev components availability**: Based on file readability results from Check 4.1, confirm D_dev components (training data, validation data, pre-trained models, etc.) are present and accessible within the data files.
2. **Cross-setting dependency handling**: When a D_dev pretrained model is identified as a cross-setting dependency (Algorithm A's output from another setting in the same paper, recorded in `setting_dependencies`), it is classified as `algorithm_output` and excluded from the data directory. This does NOT count as "missing" — the Solver derives it by first solving the source setting. The source setting itself must pass Check 4.2 independently.

### Pass condition
Per-setting: all required D_dev components for that setting are present and accessible. Overall: at least one setting passes.

---

## Check 4.3: Data Separability Verification

**Corresponding Level 3 rule**: Rule 3.3 (Evaluation Loop Completeness)

**Level 3 did**: Verified D_eval is logically decomposable into X_test and Y_ref based on paper description and repository inspection

**Level 4 does**: Parse data files to confirm d_dev/d_eval can be separated and d_eval can be decomposed into X_test/Y_ref. Assess the difficulty level of each separation. Verification only — no actual splitting, but the output must provide structured information sufficient for downstream physical file splitting.

### Criteria

For each evaluation setting, verify **two levels of separability**:

#### 4.3a: d_dev / d_eval Separability

- Verify that development data and evaluation data can be distinguished and separated
- Separation methods vary: physically separate files/directories, split markers within shared files (keys, indices, columns), external index files, or script-based splitting — see Difficulty Level Assessment below
- **split_procedure scope**: Each step in the procedure must be classified:
  - Sample-level splitting operations (train_test_split, index selection) → **legitimate**
  - `data_preparation` operations the split depends on (e.g., class balancing before train/test split, subsampling to select a subset of samples, or task-defining operations) → **legitimate (must not be removed)**, these operations strictly precede the split and must be executed beforehand; annotate as applying to both D_dev and D_eval when the paper applies them uniformly
  - Algorithm A operations (feature selection, feature engineering, data augmentation) → **must not be included**
  - Evaluation-time operations (operations executed only after the Solver produces output, before metric computation — the Solver trains and infers without knowledge of them) → **must not be included**. For example: scoring-time sample filtering, output-to-reference alignment, or post-prediction transforms
- **Sample count**: Derive expected D_dev and D_eval sizes from split_procedure parameters (e.g., ratio × total, index range length) and cross-validate both against paper-reported sizes (training/validation/test set sizes) and code evaluation logic. Unexplained mismatches in either D_dev or D_eval indicate the split_procedure may be incomplete.
- **D_dev internal structure**: If the author distinguishes training and validation subsets within D_dev (e.g., separate files, explicit index ranges, or split ratios), the split_procedure should include instructions for this separation so that the data organization matches the author's original structure. This is informational — the Solver is not forced to follow the author's train/val split, but should receive the data organized consistently with the author's setup.

#### 4.3b: d_eval Internal Separability (X_test and Y_ref)

- **X_test**: Evaluation input (the problem to solve). Should include all input features available in the initial state — not just the subset Algorithm A chose to use.
- **Y_ref**: Reference answer (ground truth for metric computation). Should contain all information needed for metric computation.
- Verify they **can** be separated from the evaluation data
- Confirm sample counts match between X_test and Y_ref
- **Information preservation**: When the source file contains fields beyond X_test and Y_ref, classify each additional field into one of three categories:
  - *y_ref-component*: Required for metric computation → retain in Y_ref
  - *y_ref-leaking*: Would reveal Y_ref information but is not needed for metric computation → discard from both X_test and Y_ref
  - *auxiliary*: Independent of Y_ref → preserve in X_test

  Document all field dispositions (retained in X_test, retained in Y_ref, discarded) and their classification rationale in the extraction description.
- **ID-field alignment**: If the source data contains an identifier field (e.g., sample IDs, protein names, sequence IDs), retain it in **both** X_test and Y_ref outputs so that algorithm outputs and ground truth can be aligned downstream.
- **Inference set vs scoring set**: The data the model does inference on (X_test) and the data that ultimately enters scoring may differ — the evaluation code may filter samples or align outputs before computing the metric. `x_test.sample_count` should reflect the **inference set** (all samples the Solver must predict on), not the scoring subset.
- **extraction scope**: `y_ref.extraction` should only describe how to prepare the Y_ref **file** from source data. Evaluation-time operations (steps executed only after the Solver produces output) should not be presented as file preparation steps.

#### Difficulty Level Assessment

**Scope**: Separability only concerns sample-level splitting (which samples go to D_dev vs D_eval, which parts are X_test vs Y_ref). Do not include any parts that belong to algorithm A, such as feature engineering, data augmentation, and other preprocessing.

Assess difficulty for `dev_eval`, `eval_decomposition`, and `overall` using the following scale (same scale applies to all three):

| Level | Name | Criteria | dev_eval typical | eval_decomposition typical |
|-------|------|----------|------------------|---------------------------|
| 1 | `trivial` | **Physically separate**: Components are already in distinct files or directories. | `train/` and `test/` are independent directories | `X_test.csv` and `Y_ref.csv` are independent files |
| 2 | `simple` | **Explicitly marked**: Components share a file, but boundaries are directly defined by inherent, tabular/hierarchical structure. | HDF5 has `train`/`test` keys; CSV has `split` column | Features and label in distinct columns; HDF5 has `input`/`target` keys |
| 3 | `moderate` | **Indirectly defined**: Split procedure is fully determined but requires cross-referencing external files, executing a known straightforward algorithm with determined parameters, or running a clean author script that performs only splitting. For random splits: ratio is determined; seed follows author's choice (fixed seed if author fixed it, no seed if author didn't fix one). | Filter rows by external `test_ids.txt`; random split with determined ratio (seed per author's implementation) | Align X_test and Y_ref from different files by shared IDs |
| 4 | `complex` | **Programmatically bound**: Requires adapting author scripts, implementing non-trivial domain-specific algorithms (even with known parameters), or parsing domain-specific formats. Split logic must be isolatable from unrelated processing. | Adapt author's split script (after removing unrelated preprocessing steps); implement scaffold split with provided parameters using domain library | Extract X_test/Y_ref from domain-specific formats (e.g., BED, GFF, PDB) |
| 5 | `ambiguous` | **Under-specified**: Separation method is partially known but not uniquely determined or cleanly executed — missing required parameters, multiple valid decompositions, or split logic coupled with preprocessing. | Random split with undetermined ratio; or author fixed seed but it's unobtainable | Data contains multiple candidate label columns; task description does not specify which is Y_ref |
| 6 | `infeasible` | **Missing information**: Essential information unavailable; OR **Paper-repository inconsistency**: Paper description contradicts repo files/code, cannot objectively determine true boundaries | Paper states 80/20 split but repo provides fixed split indices whose ratio differs significantly, cannot determine which is authoritative; No split method described | Mentioned ground truth but not provided in downloaded data files |
| — | `not_applicable` | **Conceptually invalid**: Separation does not apply to the task setting. | D_dev = D_eval (same data serves both roles) | X_test = Y_ref physically identical (e.g., image compression) |

`overall` is the holistic assessment considering both dimensions — not a mechanical formula. When `dev_eval` and `eval_decomposition` levels differ, `difficulty_reason` must explain the rationale.

#### Split Parameter Specification

For `split_procedure`, provide complete, deterministic parameters by cross-referencing **both the paper and code** (paper takes precedence when they conflict):

1. **Random split**:
   - **Ratio**: Use exact determined value, not placeholders like "e.g., 0.2"
   - **Seed**: If author fixes a seed, use it; if author doesn't fix one, do not fix one either (document as "no fixed seed"). Multiple seeds → pick one and record it
   - Avoid placeholder text for determinable parameters

2. **Fixed split**: Reference the index file or split definition with exact file path and format description

3. **Cross-dataset split**: Specify which datasets serve as D_dev and D_eval unambiguously

4. **Temporal/domain split**: State the cutoff point or selection criteria explicitly and deterministically

#### Operation scope principle 

When adding, removing, or modifying any operation in split_procedure or extraction, verify it is placed at the correct data scope. For example, a `data_preparation` operation that the Solver must know about during training should be reflected on both the D_dev and D_eval sides (not described only in d_eval separability); an evaluation-time operation should not be placed in split_procedure or extraction as a file preparation step; removing an Algorithm A operation from one field should not leave it referenced in other fields' descriptions.

#### Output Format Rules

When specifying output format in `split_procedure` and `extraction`:

1. **Default to original format**: split output uses the same format as the source file (e.g., one H5 → multiple H5 files)
2. **Non-standard format exception**: when the original format cannot be preserved, convert to the nearest standard format (CSV/NPY/H5/TSV) with no information loss

Verification results are recorded in `evaluation_settings[].verification.separability` — see [output_schema.md](output_schema.md).

### Pass condition
Per-setting: `difficulty.dev_eval` is not `infeasible` AND `difficulty.eval_decomposition` is not `infeasible`; X_test and Y_ref sample counts aligned. Overall: at least one setting passes.

---

## Check 4.4: Data Consistency Verification

**Corresponding Level 3 rule**: Rule 3.4 (Data Consistency)

**Level 3 did**: Verified data source and scale are consistent with paper description based on documentation review (README, dataset pages, paper text)

**Level 4 does**: Based on the actually downloaded data, count samples, verify version, and confirm this is the dataset whose scores are reported in the paper

### Criteria

For each evaluation setting:

1. **Read actual data dimensions** from downloaded files (using inspect_data.py)
2. **Compare with paper-reported size**: Cross-reference actual sample counts against the paper's description and Level 3's Rule 3.4 results. The goal is to confirm this is the same dataset.
   - **Acceptable differences**: Minor rounding (e.g., paper says "~5000", actual is 4987), documented data_preparation steps that explain the difference (e.g., paper says "after removing invalid entries" and code shows the filtering logic), or explicitly stated subsets (e.g., paper says "we use the first 10k samples").
   - **Unacceptable differences**: Large unexplained deviations, wrong dataset entirely (e.g., downloaded MNIST but paper used CIFAR-10), unrecoverable subset selection (paper uses a subset but doesn't specify which samples), schema changes (different features/columns), or distribution shifts.
   - **Verification requirement**: When differences exist, first determine if they fall into acceptable or unacceptable categories. If claiming a difference is acceptable, you MUST cite concrete evidence (paper text, code comments, README) that explains it. Differences without supporting evidence are unacceptable and FAIL the check.
3. **Version check**: Verify the downloaded data matches the paper's specific version or temporal snapshot.
4. **Score reporting verification**: Confirm the acquired dataset is the one whose performance scores (measured on the metrics identified in `task_info.metrics`) are reported in the paper. Cross-reference with `metrics[].score_source`. If `score_source` is incomplete or incorrect, flag for correction.

### Pass condition
Per-setting: confirmed as the same dataset (sample counts consistent, version correct, score reporting verified). Overall: at least one setting passes.

---

## Check 4.5: Evaluation Setting Validity & Experiment Closure Verification

**Corresponding Level 3 rule**: Rule 3.5 (Partial Experiment Closure)

**Level 3 did**: Determined per-setting completeness based on link accessibility and documentation review

**Level 4 does**: First validates evaluation setting structure (merge/split/remove/scope/eval method), then synthesizes Check 4.1–4.4 results to determine actual per-setting completeness, and finally verifies task unity across passing settings.

### Criteria

#### Step 1: Evaluation Setting Validity

Review **all settings** (both `evaluation_settings[]` and `rejected_settings[]`) against the paper and actual downloaded data:

1. **Should merge?** Multiple settings sharing identical data files AND same Y_ref semantic space → merge into one setting (differences are Algorithm A variants, not distinct evaluation settings). The task environment contains all data; the algorithm decides what to use. If Y_ref has a different semantic space (e.g., binary vs multi-class classification — different questions being answered), they are legitimately separate. If a single model predicts multiple targets on the same test samples (multi-objective prediction), all targets share one Y_ref semantic space — per-target metrics are evaluation dimensions of one setting, not separate settings.
2. **Should split?** Single setting that conflates multiple independent evaluations — e.g., treating a shared-training-multiple-testing / leave-one-out cross-dataset experiment as a single setting instead of N → split into separate settings.
3. **Should remove?** Settings not reflecting the paper's main claims (auxiliary analysis, ablation studies, sensitivity analysis, toy examples) → move to rejected_settings
4. **Scope too narrow?** Setting's D_dev or D_eval unnecessarily narrowed to match A's specific usage → expand to maximum available scope
5. **Invalid eval method?** K-fold cross-validation (D_eval rotates, no fixed test set) → move to rejected_settings with reason `invalid_eval_method`
6. **Missing setting?** Dataset reported in paper's main result tables but absent from both evaluation_settings and rejected_settings → add to evaluation_settings if data is acquirable, otherwise add to rejected_settings with reason

Record all structural changes in `data_check_corrections.txt` with evidence.

#### Step 2: Base Completeness
For each evaluation setting (after Step 1 adjustments, including any recovered from `rejected_settings`), it is **conditionally complete** if and only if ALL of:
- Check 4.1: Its data files are downloaded, intact, and readable
- Check 4.2: Its D_dev components are present and accessible
- Check 4.3: Separability difficulty is not `infeasible` for both dev_eval and eval_decomposition
- Check 4.4: Sample counts consistent with paper, correct version, score-reported dataset confirmed
- Any newly discovered required datasets/components or acquisition-route adjustments have been fully executed and verified (otherwise data-incomplete)
- **Cascade failure**: If this setting is a dependent setting in `setting_dependencies`, its source setting must also be conditionally complete; source failure cascades to all its dependent settings

#### Step 3: Task Unity Check
If multiple settings pass Step 2, verify they all serve a **unified research goal**:
- **Same core algorithm/method** proposed by the paper
- **Same problem domain** (e.g., all molecular property prediction, all image classification)
- **Same evaluation paradigm** (e.g., all measure prediction accuracy, all measure generation quality)

Settings using the same primary repository/entry scripts and measuring the same evaluation paradigm are confirmed as **complete**. Metrics may differ by task type (e.g., RMSE for regression, ROC-AUC for classification) as long as they measure the same paradigm.

- Settings requiring fundamentally different codebases, solving different problems, or having incompatible evaluation goals are **rejected** (reason: `Incompatibility: task disunity`).
- If no settings share task unity, retain only the most representative setting (the paper's primary/main experiment) and reject the rest.
- Record `"unified": true` if all Step 2 passing settings share task unity, `false` otherwise.
- If `task_info.metrics[]` contains entries not used by any complete setting, remove them and record each removal as a task_info correction.

#### Step 4: Core Experiment Representativeness

When settings are rejected for `invalid_eval_method`, verify the final set of complete settings still contains the paper's core experiments. If ALL core benchmarking settings (primary A-vs-baseline comparison, main result table with the most baselines, results cited in abstract/conclusion, broadest experimental scope) were rejected for `invalid_eval_method` and the surviving complete settings are solely supplementary (generalization tests, cross-dataset transfer, blind validation on subsets, etc.) → Check 4.5 `passed` = false. Record in reason: "All core benchmarking experiments are rejected; remaining settings are supplementary validation only — insufficient to represent the paper's primary claims."

### Pass condition
At least one evaluation setting is confirmed **complete** (passing Steps 1–4).

---

## Level 4 Overall Pass Condition

Level 4 `passed` = Check 4.5 `passed` (i.e., at least one setting is fully verified).

Individual checks may fail for some settings without failing Level 4, as long as the closure check (4.5) confirms at least one complete setting.
