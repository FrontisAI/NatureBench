# Check Rules: Filter-Verify (C1–C10)

---

## Terminology

- **T = (A, Data, M, S, B)**: ML task tuple
- **Algorithm A**: The core algorithm proposed by the paper (the authors' contribution in this paper), including all named variants
- **D_dev**: Development data — initial state before A starts
- **D_eval = (X_test, Y_ref)**: Evaluation data

---

## C1: Rule 1.1 Judgment Verification

**Goal**: Determine whether the paper genuinely has an ML contribution that can be extracted as a benchmark task.

### Test Sequence

Execute in order; the first test that triggers determines the outcome:

#### Test 1: Off-the-shelf ML Detection

Identify the ML model used in the paper and answer:
1. Is the ML model used without architectural modification?
2. Is the paper's novelty in the data, physical process, or experimental design rather than in the ML model itself?

If both are true → likely should reject, proceed to Test 2 for confirmation.

**Exception**: If the paper's novelty is in task formalization (defining a new ML task with novel input/output/objective), proceed to Test 4 to assess whether the formalization itself constitutes the primary contribution.

If the ML model has non-trivial modifications (new layers, new loss function, new training procedure, new architecture design) → pass Test 1, skip to Test 4.

**Notes**:
- Hyperparameter tuning, data augmentation, or changing input data type alone do not count as "architectural modification"
- `methodological_adaptation` requires **structural/architectural-level** domain-specific design of the model (e.g., GNN variants designed for special properties of molecular graphs), not merely applying a general model to new data
- Using a pre-trained model for fine-tuning: if the fine-tuning process itself is the paper's contribution (e.g., designing a novel fine-tuning strategy) → counts as modification; if it's just standard fine-tuning → does not count

#### Test 2: Non-ML-Method Impact Pattern

Does the paper match the following pattern?
> "The core comparison is between different non-ML-method factors (data, domain knowledge, signals, etc.), using the same or off-the-shelf ML model"

**Specific indicators**:
- The main comparison is "factor X vs. factor Y, same model architecture"
- The paper's conclusion is "our factor/approach improves model performance" rather than "our model/method improves on the task"
- Removing the non-ML innovation leaves no ML contribution
- The ML model is interchangeable (any standard model would show the same advantage)

**Non-ML-method factors** are external factors that do not contain learnable parameters, do not modify model architecture, and are not part of the learning algorithm itself.

**Specific examples**:
- **Data representations**: Hand-crafted deterministic transformations
- **Data sources**: Dataset selection, data modality, acquisition devices, data scale, noise characteristics,
- **Domain knowledge**: External constraints, scientific rules, expert heuristics
- **Training signal**: Label quality, annotation granularity, label sources

**NOT non-ML factors**:
- Learned representations (word2vec, VAE latent spaces)
- Architecture-level knowledge integration (PINNs structure, GNN inductive biases)
- Loss function design, reward shaping

If yes → **reject**, Rule 1.1, category `rejected_other_out_of_scope`

#### Test 3: Data Generation/Augmentation Pattern

Does the paper match the following pattern?
> "Algorithm A produces intermediate data (synthetic samples, augmented features, etc.) that is not directly evaluated; instead, evaluation relies on separate downstream ML models that must be trained on A's output"

Specific indicators:
- A's output is intermediate material (synthetic data, augmented features, learned representations, etc.), not a directly evaluated end-task output (whether that output is a prediction, a generated structure, a computed score, or any other final deliverable)
- Evaluation requires feeding A's output into separate downstream **ML models** (SVM, kNN, neural networks, etc.) that are **trained from scratch** on A's output
- The downstream models are not part of A's contribution

**Important distinction**: This test applies when evaluation depends on **trainable ML models**. It does NOT apply when evaluation uses **deterministic computational tools** (e.g., physics simulators, chemical validity checkers like RDKit, energy calculators like Rosetta, eigenvalue computations). Such tools directly assess the quality of A's output without requiring training.

Examples:
- **Reject**: GAN generates images → train SVM classifier on generated images → evaluate SVM accuracy (downstream ML model trained on A's output)
- **Pass**: GAN generates molecular structures → RDKit computes validity → evaluate generation quality (deterministic tool, no training)
- **Pass**: GAN generates kinetic parameters → physics simulator computes eigenvalues → evaluate parameter quality (deterministic tool, no training)

If yes → **reject**, Rule 1.1, category `rejected_other_out_of_scope`

#### Test 4: Algorithmic Innovation Space Test

Ask: "If an ML researcher received D_dev and D_eval, what would they change to beat SOTA?"

- If the answer involves designing a better model/architecture/loss function/training method → algorithmic innovation space exists → **pass**
- If the answer is to collect better data/change physical equipment/modify experimental design → no algorithmic innovation space → **reject**

#### Test 5: Category Correctness

If the paper passes Rule 1.1, verify whether the assigned category is accurate.

**Pass categories** (must satisfy the stated criteria):

| Category | Criteria |
|----------|----------|
| `algorithmic_innovation` | Proposes mathematical-level improvements to model architecture, loss function, optimizer, or sampling strategy. Examples: new Attention mechanism, new regularization method, new training strategy |
| `problem_formulation` | Proposes a novel task formalization that converts a scientific problem into a clear ML task (input/output/objective), where the formalization itself constitutes the primary contribution. Must validate ML effectiveness on this task. Should introduce new input representations, output spaces, or objective functions—not merely apply existing models to standard tasks. Examples: defining protein folding as end-to-end distance matrix prediction, formulating drug response as graph-level regression |
| `methodological_adaptation` | Adapts general ML methods (e.g., Transformer, GNN) for a specific domain with non-trivial structural/architectural engineering or design work tailored to the domain. Examples: GNN variants designed for special properties of molecular graphs |

If the paper was rejected by filter_result.json, verify whether the assigned reject category is accurate.

**Reject categories** (must match the paper's characteristics):

| Category | Criteria |
|----------|----------|
| `rejected_validation_tool_usage` | ML is only used as a standard data analysis tool to support conclusions of non-ML research (experimental, theoretical, or observational studies), with no new ML-driven insights. |
| `rejected_non_computational` | Only involves wet lab experiments; OR pure theoretical derivation; OR hardware implementation without data-driven components |
| `rejected_non_ml_factor_comparison` | Core comparison is between different non-ML-method factors (data sources, domain knowledge, training signals, etc.), using the same or off-the-shelf ML model |
| `rejected_intermediate_data_evaluation` | Algorithm A produces intermediate data evaluated via separate downstream ML models trained on A's output, not via direct end-task metrics or deterministic tools |
| `rejected_attribution_explainability` | Core contribution is an attribution method or explainability framework focused on interpreting model behavior rather than improving a quality metric |
| `rejected_general_methodology` | Proposes a general training strategy or optimization paradigm for multiple diverse models/tasks, not tied to a specific task instance; verification requires implementation across different base model architectures |
| `rejected_hardware_dependent` | Algorithm cannot run on general-purpose computing hardware (real-time physical interaction dependency or non-standard hardware dependency) |
| `rejected_other_out_of_scope` | Does not fit pass conditions (A, B, or C) and does not neatly fall into the specific reject categories above; used for papers that fail the end-to-end task tuple extraction paradigm |

**Special case — Coexistence of Computational and Wet Lab/Physical Experiments**: When a paper contains both computational and wet lab/physical experiments, determine the role of the wet lab part:
- **Pass**: Wet lab experiments only serve as validation of the computational method. The core contribution remains the computational/ML method itself.
- **Reject**: Wet lab experiments are the paper's primary research content or core contribution. The computational part plays an auxiliary or screening role.

Wrong category → record correction but do not change pass/reject status.

#### Hardware-Dependent Execution Check

Verify that the algorithm can run on general-purpose computing hardware (CPU/GPU/TPU):

- **Reject if**: real-time physical device interaction required (e.g., must connect to electron microscope for real-time parameter adjustment), or depends on non-standard instruction sets / specific proprietary hardware accelerators (e.g., FPGA)
- **Pass if**: algorithm runs on standard hardware. When data has already been collected and is downloadable, the acquisition equipment (drones, microscopes, etc.) does not constitute hardware dependency.

---

## C2: Rules 2.1, 2.2 Judgment Verification

**Goal**: Spot-check non-data rules for obvious errors.

### Rule 2.1: Performance Absoluteness

**Core question**: Does Algorithm A achieve competitive quality on a recognized quality metric, such that the reported SOTA S serves as a meaningful, challenging benchmark?

**Pass conditions**:
- The paper's primary comparison metric (the metric justifying Algorithm A's superiority or SOTA status) is a quality metric from the whitelist below
- Algorithm A achieves quality performance at or above the best baseline reported in the paper
- Note: merely reporting a whitelist metric is insufficient — it must be the metric where A demonstrates its primary advantage

**Quality metric whitelist** (allowed as core winning criteria):
- Classification/Detection: Accuracy, Precision, Recall, F1-Score, AUC-ROC, mAP
- Regression: RMSE, MAE, MSE, R²
- Correlation: Pearson Correlation, Spearman Correlation
- Generation/Translation: BLEU, ROUGE, METEOR, CIDEr
- Language Models: Perplexity (PPL)
- Reinforcement Learning: Success Rate, Cumulative Reward
- Structure Prediction: GDT-TS, TM-score, LDDT, RMSD
- Image Quality: PSNR, SSIM, FID, IS
- Other Quality Metrics: IoU, Dice Score, Edit Distance, etc.

**Reject conditions**:
- The paper's core winning criterion is an efficiency/resource metric: Inference Latency, Training Time, FLOPS, Parameter Count, Peak Memory Usage, Energy, Throughput, GPU Utilization, etc.
- The paper's core winning criterion is based on model analysis: Interpretability/Explainability analysis, Visualization analysis, Qualitative case studies

**Special scenario — ML Replacing Traditional Methods**: If the paper uses ML to replace traditional time-consuming methods (e.g., physics simulation), "acceleration" is the motivation, not the core contribution. The core contribution is quality performance on the task. Such papers pass if quality metrics are the primary basis for comparison.

### Rule 2.2: Metric Determinism

**Pass conditions** (all three must hold):
1. **Deterministic function**: `Score = M(Y_out, Y_ref)` — the metric is a function of only the algorithm's output and the reference
2. **Fully automated**: Given Y_out and Y_ref, a unique numerical value can be computed without human intervention. For Oracle-type tasks, M may involve running a simulator or scoring function; this is acceptable as long as the scorer is reproducible and locally executable.
3. **Reproducible**: Same input must always produce same output

**Reject conditions**:
- Human Subjective Evaluation: human study/judgment as the core evaluation criterion (human evaluation as auxiliary qualitative demonstration is allowed, but cannot be the core criterion)
- Visual Inspection: relies on manual visual inspection to judge result quality (exception: CV tasks with pixel-level Y_ref, e.g., segmentation with ground truth mask)
- Black-box Evaluation Tools: metric computation depends on proprietary software not disclosed by the paper, or on domain-specific expert knowledge bases that are not accessible
- Algorithm A-Dependent Evaluation: evaluation mechanism requires a component of Algorithm A itself (e.g., A's discriminator, encoder, learned reward model) to compute scores — leaks method information
- Non-reproducible External Service: evaluation depends on an external service or API with no locally executable alternative

---

## C3: Rules 3.1-3.6 Judgment Verification

**Goal**: Verify data completeness judgment, focusing on evaluation settings coverage, setting identification, and evaluation method validity.

### C3.1: Setting Identification

Review all `evaluation_settings[]` and `rejected_settings[]` against the paper:

1. **Should merge?** — Multiple settings that use identical data files AND have the same Y_ref semantic space. Key test: would merging change D_eval's meaning? If Y_ref has the same label space and samples, the settings should be merged (differences are Algorithm A variants, not distinct evaluation environments). If Y_ref has a different semantic space (e.g., binary vs multi-class classification — different questions being answered), they are legitimately separate. If a single model predicts multiple targets on the same test samples (multi-objective prediction), all targets share one Y_ref semantic space — per-target metrics are evaluation dimensions of one setting, not separate settings.

2. **Should split?** — A single setting that conflates multiple independent evaluations — e.g., treating a shared-training-multiple-testing / leave-one-out cross-dataset experiment as a single setting instead of N.

3. **Should remove?** — Settings that don't reflect the paper's main claims (ablation studies, sensitivity analysis, result visualization, auxiliary wet lab validations, trivial toy settings).

4. **Maximum scope** — Each setting should use the broadest data scope that Algorithm A's variants collectively accessed, not just the subset one specific variant chose to use. This applies when different variants of A use different subsets of the same underlying data source (e.g., one uses a subset of columns while another uses all, or one uses the main file while another additionally uses supplementary files). The setting should include the union of all data accessed by any A variant (the superset). **Notes**: This does NOT mean expanding beyond what the paper's experiments actually used to include external data the authors never accessed/used.

5. **Task unity** — All remaining settings should serve a unified research goal:
   - **Same core algorithm/method** proposed by the paper
   - **Same problem domain** (e.g., all molecular property prediction, all image classification)
   - **Same evaluation paradigm** (e.g., all measure prediction accuracy, all measure generation quality)

   Settings should use the same primary repository/entry scripts and measure the same evaluation paradigm. Metrics may differ by task type (e.g., RMSE for regression, ROC-AUC for classification) as long as they measure the same paradigm.

6. **Cross-setting dependency verification** — When the paper describes a pretrain→finetune or transfer learning pipeline where one setting's trained model is used as another setting's pretrained initialization:
   - If `setting_dependencies` is absent or incomplete → `missing_cross_setting_dependency` (recommended: add the dependency)
   - If `setting_dependencies` records a dependency but the paper shows the pretrained model is from external published work (not Algorithm A in this paper) → `incorrect_cross_setting_dependency` (recommended: remove the dependency; the model is a legitimate external resource)
   - If source setting is in `rejected_settings` but its dependent settings are in `evaluation_settings` → `cascade_violation` (recommended: reject the dependent settings too)

### C3.2: Evaluation Settings Completeness

1. From the paper text, identify all datasets in **main result tables/figures** (exclude ablation studies, sensitivity analysis, visualization)
2. Compare against `evaluation_settings[]` + `rejected_settings[]`
3. Datasets in the paper but in neither list → `missing_setting`
4. Datasets in the lists but not in the paper's main results → `extra_setting`

### C3.3: Evaluation Method Validity

For each evaluation setting, confirm the paper's evaluation method:

| Evaluation Method | Validity | Notes |
|-------------------|----------|-------|
| Fixed split (split files or indices provided) | Valid | — |
| Random splits (multiple seeds/ratios) | Valid | Parameters determined at data-check stage |
| K-fold cross-validation (sole evaluation method) | Invalid | D_eval is not fixed; should go to rejected_settings |

If filter_result.json accepted a setting that only uses K-fold CV → `invalid_eval_method`

### C3.4: rejected_settings Completeness

- Are there settings that should be excluded but are not?
- Are rejection reasons specific and correct?

### C3.5: Per-Setting Metric Coverage

For each accepted evaluation setting, verify that the paper reports scores for that setting on at least one metric from `task_info.metrics` (i.e., metrics that passed Level 2 validation). A setting with no Level 2-validated metric scores should not be in `evaluation_settings`.

### C3.6: Data Scale Feasibility (Rule 3.6)

Verify the size estimation judgment in `filtering_process` Rule 3.6:

1. **Tier assignment consistency**: Does `task_info.data.size_tier` match Rule 3.6's `size_tier`? If mismatch → correct task_info.
2. **Estimation reasonableness**: Cross-check `per_url_estimates` against paper text mentions of data size. If the paper mentions a specific size (e.g., "50GB dataset") but the estimation shows a vastly different number (>5x discrepancy) → `size_estimation_mismatch` (informational, does not change the pass/reject decision).
3. **Rejection correctness**: If Rule 3.6 rejected (L tier or indeterminate), verify there is no obvious accessible size information that was missed. If size information was available but not captured → `missed_size_information`.
4. **Pass correctness**: If Rule 3.6 passed with a low-confidence estimate, verify the paper text doesn't clearly indicate a much larger dataset → `underestimated_size`.

---

## C4: Algorithm A and SOTA Definition

**Goal**: Verify that `task_info.algorithm` and `task_info.sota` are correctly defined.

### Algorithm A Check

- Does Algorithm A cover **all variants** proposed by the paper? (Base method + all named variants)
- Is the definition clear and complete?
- Example: Paper proposes MolMapNet-B/D/F → algorithm should include all three

### SOTA Check

- SOTA should be equivalent to Algorithm A (including all variants), consistent with `task_info.algorithm`
- Does the description clearly list all variants rather than using vague phrasing (e.g., "depending on dataset")?

---

## C5: Algorithm A Boundary (D_dev Components)

**Goal**: Verify that D_dev descriptions do not include Algorithm A outputs.

### Procedure

For each evaluation setting, examine `d_dev.description` and `d_dev.source.instruction`:

1. Check for **obvious Algorithm A outputs** mixed into D_dev. Watch for:
   - Pre-training outputs proposed by the paper (feature maps, embeddings, model weights) placed in D_dev
   - Results of the paper's proposed feature selection/engineering placed in D_dev
   - Intermediate products from the paper's processing pipeline treated as initial-state data
   - Cross-setting pretrained models: if a setting's D_dev lists a pretrained model that is actually trained by Algorithm A in another setting of the same paper, it should not be classified as `external_resource` — it is an `algorithm_output`. Check that such cases are correctly reflected in `setting_dependencies` (verified in C3.1 step 6).

2. For each suspicious component, ask: "Is this specific to Algorithm A's approach, or would any method working on this task need similar data?"
   - Specific to A (only this method needs it) → should NOT be in D_dev
   - Method-agnostic (any approach would need similar input) → legitimate D_dev

3. Note: fine-grained classification of D_dev components (data_preparation vs. algorithm_preprocessing_output) is deferred to data-verify, which has access to actual code and files. At this stage, only flag clear violations visible from the paper text.

---

## C6: Metrics Completeness

**Goal**: Verify that `task_info.metrics` lists all qualifying metrics from the paper's main result tables — and only those metrics.

### Qualifying criteria

A metric should be in `task_info.metrics` only if it satisfies all four:
1. Used to evaluate Algorithm A in main result tables/figures (not ablation studies, sensitivity analysis, or auxiliary demonstrations)
2. Is a quality metric (not efficiency/resource metrics or analysis-only metrics)
3. Has explicit score reporting with a traceable source (Table X, Figure Y)
4. Individually satisfies Rule 2.2 Metric Determinism — the metric's computation in this paper does not involve human evaluation, visual inspection, proprietary tools, Algorithm A's own components, or non-reproducible external services

### Procedure

1. Identify all metrics in the paper's main result tables that meet the qualifying criteria above
2. Compare against `task_info.metrics[].name`
3. Qualifying metric in paper but not in task_info → `missing_metric`
4. Metric in task_info but does not meet qualifying criteria → `extra_metric`
5. `score_source` missing, incorrect, or does not list all main result tables/datasets where the metric appears → `invalid_source`

---

## C7: Evaluation Setting Component Correctness

**Goal**: Verify that each evaluation setting's component descriptions are accurate.

### C7.1: Task Type and Metric Consistency

Does the task type stated in each setting's description match the metric used?

| Metric | Expected Task Type |
|--------|-------------------|
| ROC-AUC, Accuracy, F1, Precision, Recall | Classification |
| RMSE, MAE, MSE, R², Pearson | Regression |
| BLEU, ROUGE, Perplexity | Generation/Language |

Mismatch → correct the task type or metric.

### C7.2: D_dev and D_eval Description Correctness

- **d_dev**: Does it accurately reflect the training/validation data described in the paper? Are important components missing (pre-training dependencies, external resources)? **Exception**: when `setting_dependencies` indicates that a pretrained model comes from another setting's Algorithm A training (cross-setting dependency), it is correctly absent from d_dev as an available resource — do not flag as missing.
- **d_eval.x_test**: Does it correctly describe the model input? Should include all input features available in the initial state, not just the subset A chose to use.
- **d_eval.y_ref**: Does it correctly describe the evaluation reference/ground truth? Verify the Y_ref type is correctly identified and the description matches:
  - Label (static ground truth): should describe ground truth data — labels, scores, reference structures, etc.
  - Oracle (deterministic computable function): should describe the computational tool (simulator, scoring function, validity checker, etc.) and its obtainability
  - Distribution (target distribution / quality reference): should describe reference sample set, distribution statistics, and/or quality evaluation oracles

### C7.3: Data Source Accuracy

- Does the URL point to the resource described in the paper?
- Is `acquisition_scenario` consistent with the actual acquisition method?
- Is the data described in each setting the same data the paper used to produce the scores reported in its main result tables? If the data source points to a different dataset, version, or subset than what produced the reported scores → correct the source.

### C7.4: Sample Size/Scale Consistency

- Does the sample count in descriptions match what the paper reports (Table 1 or Methods)?
- Obvious inconsistency (>10% deviation) → correct

---

## C8: Data Pattern Correctness

**Goal**: Verify that `data.pattern` matches the actual structure of evaluation_settings.

| Pattern | Expected Structure |
|---------|-------------------|
| Multiple Independent | Each setting has independent D_dev and D_eval |
| Shared Training, Multiple Testing | Multiple settings share D_dev, each with independent D_eval |
| Combined Training | Multiple settings' D_dev merged from different sources |
| Paired Combinations | Different data combinations (e.g., A+B, A+C, B+C) form independent loops |
| Leave-One-Out Cross-Dataset | Each rotation uses a different dataset as D_eval and the rest as D_dev |
| Single Dataset | Only one setting |

> If the paper's dataset does not fit the above patterns, handle flexibly based on the actual situation.

Mismatch → correct the pattern or adjust settings.

---

## C9: Internal Consistency

**Goal**: Verify that task_info fields are consistent with paper evidence, using filtering_process as a cross-reference.

**Priority principle**: task_info is the correction target. filtering_process is a process record from paper-filter — when task_info diverges from filtering_process, verify against the paper to determine which is correct, then correct only task_info if needed. Do not generate corrections for filtering_process fields. If both are inconsistent with the paper, correct task_info to match the paper.

### Check Items

1. **Rule 3.5 vs task_info.data**: Does the `evaluation_settings` list in `filtering_process` Rule 3.5 match `task_info.data.evaluation_settings`? (Names, count, task type/metric). If mismatch, verify against paper and correct task_info.

2. **Rule 2.1 vs task_info.metrics**: Does `metrics_identified` in `filtering_process` Rule 2.1 match `task_info.metrics`? If mismatch, verify against paper's main result tables and correct task_info.

3. **Algorithm description consistency**: Does `task_info.algorithm` match the algorithm description in `filtering_process` Rule 1.1? If mismatch, verify against paper and correct task_info.

4. **Cross-setting consistency**: Are shared resources (e.g., pre-trained model files) described consistently across settings in task_info?

**Note**: filtering_process serves as a reference to identify potential task_info errors. All corrections should target task_info fields only, as task-build uses task_info downstream.

---

## C10: Intra-Setting Terminology Consistency

**Goal**: Ensure key terminology (dataset names, sample counts, feature counts, class counts, etc.) is consistent across all descriptive fields within the same evaluation_setting.

### Scope

For each `evaluation_settings[i]`, check consistency across:
- `setting.description`
- `d_dev.description`
- `d_eval.description`
- `d_eval.x_test`
- `d_eval.y_ref`

### Check Items

1. **Dataset name consistency**: If a dataset is named in one field (e.g., "10X PBMC"), all other fields should use the same name, not variants like "PBMC 10X" or "10X Genomics PBMC"

2. **Numerical consistency**: Sample counts, feature counts, class counts, etc. must match across all fields
   - Example: If `setting.description` says "2,100 cells", then `d_eval.x_test` should not say "2100 samples" or "~2k cells"

3. **Terminology consistency**: Use consistent terms for the same concept
   - Example: Don't mix "cells" and "samples", "genes" and "features", "clusters" and "classes" when referring to the same thing

4. **Version/subset consistency**: If one field mentions a specific version or subset (e.g., "subsampled", "filtered", "v2"), other fields should clarify the same

### Detection Strategy

When a correction is made to any field in a setting, check if similar outdated wording appears in other fields of the same setting. Flag all instances that need updating.
