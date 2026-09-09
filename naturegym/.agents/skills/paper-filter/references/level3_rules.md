# Level 3: Data and Process Completeness Filtering

Level 3 screens for data feasibility: whether the paper's data is accessible and whether the evaluation structure can support a benchmark task. The goal is to confirm that the complete data environment for training and evaluation (D_dev + D_eval) is obtainable — not merely enough data to recompute Algorithm A's reported scores, but all data a Solver would need to independently train and evaluate any approach on the same task. Verification is based on paper text, link validation, and data source inspection — without downloading data files.

## Inspection Strategy

Level 3 does **not** download data files. Available verification methods:

- **Link validation**: Check accessibility via HTTP status codes using `scripts/validate_links.py`
- **Data source inspection**: Browse repository contents (directory structures, file names, file sizes), view file contents where platforms allow (e.g., CSV headers on GitHub, dataset previews on HuggingFace, file descriptions on Zenodo), review documentation (README, data description pages, dataset cards)
- **Paper text analysis**: Check Data Availability, Methods, Supplementary, figure/table captions for data-related information

**Judgment principle**: Use link validation and data source inspection to corroborate paper claims where possible. When a claim cannot be verified at this stage (e.g., exact sample counts require downloading), record the paper's claim as-is. Do not reject solely because a claim is unverifiable — reject only when evidence clearly contradicts the claim or when links are inaccessible.

---

## Rule 3.1: Zero-Interaction Acquisition

### Pass Conditions

All necessary files constituting Data = {D_dev, D_eval} must satisfy any of the following conditions:
- Directly downloadable via public links (HTTP/HTTPS/FTP)
- Obtainable via DOI
- Obtainable via public storage services (S3/HuggingFace/Zenodo/Figshare)
- Obtainable via personal cloud storage public share links (Google Drive/Dropbox/Baidu Netdisk/OneDrive, etc.), as long as the link can be downloaded without login
- Obtainable via APIs that don't require manual approval

> **Note**: The data obtainable must support the **complete** algorithm A. If data is only available for a sub-component, Rule 3.1 is **failed**.

### Reject Conditions

**Reject: "Available upon request"**
- Data requires email application
- Data requires filling out application forms and waiting for approval

**Reject: Requires Signing Agreement**
- Requires signing Non-Disclosure Agreement (NDA)
- Requires signing Data Use Agreement (DUA)

**Reject: Identity Authentication Requirements**
- Requires specific institutional authentication (e.g., hospital, government, specific university)
- Requires proof of researcher identity

### Judgment Method

1. Identify all data components required for the task:
   - D_dev: Training data, validation data, pre-trained weights, external dependencies, etc.
   - D_eval: X_test (input data), Y_ref (ground truth/reference)
2. For each data component, locate its source link from the paper
3. Use `scripts/validate_links.py` to verify **all** identified links
4. A single inaccessible critical link results in rejection (unless Rule 3.5 applies)

**Link-TaskInfo Consistency Constraint**: Every `url` extracted under `task_info.data.evaluation_settings` (i.e., `d_dev.source.url` and `d_eval.source.url`) MUST have a corresponding verification entry in Rule 3.1's `links_checked`.

---

## Rule 3.2: Initial State Completeness

### Purpose

Check whether D_dev dependencies mentioned in the paper appear to be obtainable, based on paper text and data source inspection.

### Pass Conditions

D_dev must satisfy Dependency Closure (see core_definitions.md § D_dev): all prerequisites required for algorithm A to run must be obtainable.

> **CRITICAL Note:**
> * **D_dev represents the INITIAL STATE before Algorithm A starts.** It only includes information that objectively existed *prior* to solving the problem.
> * **DO NOT INCLUDE outputs or intermediate products of Algorithm A itself** (e.g. weights from A's own training step, or data from A's own preprocessing step).
> * **Boundary test**: For each data component, ask "Is this specific to Algorithm A's approach, or would any method working on this task need similar data?" If only Algorithm A needs it → not D_dev. If any approach would need similar input → legitimate D_dev.
> * The filtering goal is task extraction, not reproduction. D_dev refers to data dependencies only. Implementation code for the proposed method or baselines is not part of D_dev.

### Reject Conditions

**Reject: External Pre-trained Model Not Obtainable**
- Paper explicitly states the algorithm is fine-tuned on an external pre-trained model, but that pre-trained model's weights are not public
- Note: If pre-training is part of algorithm A itself (i.e., the paper pre-trains from scratch), this does not apply

**Reject: Private External Dependencies**
- Paper depends on authors' private external knowledge bases, vocabularies, or simulator environments, and these are not included in the download package

**Reject: D_dev Data Cannot Be Located**
- Repository only contains derivative artifacts (plotting data, result analysis, experiment outputs/results) without actual training/development data

**Reject: Data Anomalies**
- Data links are broken
- Repository README indicates data is incomplete or placeholder

---

## Rule 3.3: Evaluation Loop Completeness

### Purpose

Check whether D_eval appears to be decomposable into X_test and Y_ref, based on paper description and data source inspection.

### Pass Conditions

D_eval must be decomposable into X_test (problem input) and Y_ref (reference for computing metrics), as defined in core_definitions.md § D_eval. What constitutes "Y_ref exists" depends on the Y_ref type:

| Y_ref Type | What to check for |
|------------|-------------------|
| **Label** (static ground truth) | Ground truth data file — labels, scores, reference structures, etc. |
| **Oracle** (deterministic computable function) | Reproducible, locally executable computational tool (simulator, scoring function, validity checker, objective function, etc.) — must be obtainable, not proprietary |
| **Distribution** (target distribution / quality reference) | Reference sample set, distribution statistics, and/or quality evaluation oracles |

### Reject Conditions

**Reject: Problem Without Solution**
- Paper only describes input data X_test with no mention of Y_ref for verification
- No ground truth, oracle function, or reference data is described or discoverable

**Reject: D_eval Data Cannot Be Located**
- Repository only contains derivative artifacts (plotting data, result analysis, experiment outputs/results) without actual evaluation data (X_test or Y_ref)

**Reject: Data Anomalies**
- Data links are broken
- Repository README indicates data is incomplete or placeholder

---

## Rule 3.4: Data Consistency

### Purpose

Check whether data version and scale appear consistent with the paper's claims, based on data source inspection (README, file listings, dataset pages, file sizes).

### Pass Conditions

The data being verified must be the same data the paper used to produce scores. Data version and scale must be consistent with the paper's description:
- **Source Consistency**: The obtainable data source (source / version) matches the paper description
- **Scale Consistency**: The obtainable data scale is consistent with what the paper reports. Minor discrepancies are acceptable when they have legitimate causes — e.g., the paper reports an approximate/rounded number, or data preprocessing (filtering, deduplication) reduces the count from the raw source. Obvious order-of-magnitude mismatches are not acceptable.

### Reject Conditions

**Reject: Scale Inconsistency** (only when clearly detectable)
- Repository only provides mini/toy/sample/demo/example data, not the complete dataset
- Common indicators: filename contains toy/sample/demo, or README states for testing only

**Reject: Severe Version Mismatch**
- Paper experiments on v1.0, public link only provides v2.0
- Paper experiments on data from Jan 2021, but public link only provides dynamically updated data from 2023 (and historical snapshots are unavailable)
- Paper uses private internal dataset, public version is Demo data

**Reject: Unclear Version**
- D_eval has multiple versions (e.g., v1.0, v2.0), but cannot determine which version the paper used

---

## Rule 3.5: Partial Experiment Closure

### Evaluation Setting Identification

An **Evaluation Setting** is the smallest unit for completeness verification — a (D_dev, D_eval) pair equipped with evaluation metrics that can independently form a complete experimental loop.

**Setting Identity Rule**: Settings are distinguished by their data components (D_dev and D_eval):
- **Merge condition**: Two candidate settings that share identical data files AND have the same Y_ref semantic space are the same setting — merge them, even if the paper reports them in separate tables due to different algorithmic configurations (e.g., different runtime flags, preprocessing strategies, or input utilization choices). Such differences reflect Algorithm A's design variants, not distinct evaluation environments.
- **Separate condition**: Settings with different Y_ref semantic spaces (e.g., binary vs multi-class classification — different questions being answered) are legitimately separate.
- **Multi-objective case**: If a single model predicts multiple targets on the same test samples, all targets share one Y_ref semantic space — per-target metrics are evaluation dimensions of one setting, not separate settings.

**Maximum Scope**: When algorithm A variants use different scopes of the same underlying data, adopt the broadest data scope (the superset) as the setting's data:
- Example: one variant uses a subset of columns while another uses all, or one uses the main file while another additionally uses supplementary files → use the superset.
- The task environment should contain all data that was available to the original authors; the algorithm under evaluation decides what to use.
- This does NOT mean expanding beyond what the paper's experiments actually used to include external data the authors never accessed used.

**Selection Criteria**:
- **Must Include**: Experiments supporting the paper's main claims (e.g., "Table 1: Main Results").
- **Must Exclude**: Ablation studies, sensitivity analysis, result visualization/analysis, auxiliary wet lab validations, or trivial toy settings.
- **Judge by Significance**: Whether synthetic or real-world data, if it's the primary way the paper proves A's value, it counts.
- **Coherence**: All selected settings should involve the same Algorithm A, the same general problem domain, and the same evaluation paradigm (e.g., all measure prediction accuracy, or all measure generation quality). Metrics may differ by task type (e.g., RMSE for regression, ROC-AUC for classification) as long as they measure the same paradigm. Settings from unrelated experiments should not be grouped together.

**Evaluation Setting Instances**:

| Dataset Pattern | Evaluation Setting |
|-----------------|--------------------|
| **Multiple Independent** | **N Independent Settings**: Each dataset forms a loop |
| **Shared Training, Multiple Testing** | **M Independent Settings (Shared D_dev)**: 1 training set, M test sets for generalization |
| **Combined Training** | **M Settings (Shared D_dev)**: Train on merged training set (D_dev = A_train ∪ B_train), evaluate separately on A_test and B_test |
| **Paired Combinations** | **N Independent Settings**: Different data combinations (e.g. A+B, A+C, B+C) form independent loops |
| **Leave-One-Out Cross-Dataset** | **N Independent Settings**: Each rotation uses a different dataset as D_eval and the rest as D_dev. |
| **Single Dataset** | **1 Setting**: Single dataset |

> If the paper's dataset does not fit the above patterns, handle flexibly based on the actual situation.

### Cross-Setting Dependencies

Independent of data pattern, check whether any setting's D_dev pretrained model is produced by Algorithm A's training in another setting of the same paper (pretrain→finetune / transfer learning within the paper).

- **Source setting**: Trains from scratch, D_dev independent of other settings
- **Dependent setting**: D_dev requires a pretrained model that is the source setting's Algorithm A training output

**Identification**: Look for paper text such as "fine-tune the model trained in Section X", "initialized with pretrained weights from the first stage", etc. If the paper does not clearly indicate such a dependency, do not force identification — downstream verification may discover it through code analysis.

**When detected**:
1. Record in `task_info.data.setting_dependencies`
2. In dependent setting's `d_dev.description`, state that the pretrained model originates from the source setting
3. The pretrained model is Algorithm A's output — NOT an `external_resource`. But this does not reject the dependent setting; the Solver obtains it by first solving the source setting.
4. **Cascade**: If the source setting is rejected, all its dependent settings must also be rejected.

### Evaluation Method Validity

For each evaluation setting, confirm the paper's evaluation method:

| Evaluation Method | Validity | Handling |
|-------------------|----------|----------|
| Fixed split (split files or indices provided) | Valid | — |
| Random splits (random partitioning with specified or unspecified parameters) | Valid | Exact split parameters are not required at this stage |
| K-fold cross-validation (sole evaluation method) | Invalid | D_eval is not fixed; must go to rejected_settings |

### Core Experiment Representativeness

When settings are rejected for `invalid_eval_method`, assess whether they constitute the paper's **core benchmarking** — the primary experiments demonstrating Algorithm A's superiority (main result table with the most baselines, results cited in abstract/conclusion, broadest experimental scope). If ALL core benchmarking settings are rejected and the remaining valid settings serve only a supplementary role (generalization tests, cross-dataset transfer, blind validation on subsets, etc.), the paper FAILS — supplementary experiments alone do not constitute sufficient evidence for the paper's primary claims.

### Evaluation Settings Completeness

All datasets in the paper's results must be accounted for:
1. Identify all datasets in main result tables/figures (exclude ablation studies, sensitivity analysis, visualization). When the main text references supplementary tables/figures for core results, include those as well.
2. Each dataset must appear in either `evaluation_settings` or `rejected_settings`
3. Missing datasets are errors that must be corrected before proceeding

### Pass Conditions

Each evaluation setting is independently verified against Rules 3.1-3.4. Settings that fail any rule go to `rejected_settings` with a specific `failure_reason`. **At least one** evaluation setting must simultaneously satisfy:
1. Rules 3.1-3.4 are all satisfied for that setting
2. The evaluation method is valid (not sole K-fold CV)
3. The paper reports scores for that setting on at least one metric from `task_info.metrics` (i.e., metrics that passed Level 2 validation)
4. The passing settings are not solely supplementary experiments whose core counterparts were all rejected for `invalid_eval_method` (see Core Experiment Representativeness above)

---

## Link Validation Script

Rule 3.1 requires using `scripts/validate_links.py` to verify data links. See [references/validate_links_usage.md](validate_links_usage.md) for script usage, output format, and status value definitions.

---

## Rule 3.6: Data Scale Feasibility

### Purpose

Estimate total data size without downloading, and reject papers whose data exceeds feasible processing limits or whose size cannot be determined. This rule implements zero-download size estimation inspired by AutoSoTa's Symbolic Resource Discovery approach.

### Size Tiers

| Tier | Range | Action |
|------|-------|--------|
| **S** | < 1 GB | Standard automated pipeline |
| **M** | 1 - 50 GB | Standard pipeline with size-aware processing |
| **L** | > 50 GB | **Reject** — data too large for automated pipeline |

### Estimation Method

Size estimation uses three sources, in decreasing order of confidence:

1. **Content-Length headers** (high confidence): Extracted from Rule 3.1's `links_checked[].file_size`. For compressed files (`.gz`, `.tar.gz`, `.zip`, `.bz2`), apply decompression multipliers (3x for gz/zip, 5x for bz2).
2. **Platform API queries** (medium confidence): Query APIs of hosting platforms (GitHub, HuggingFace, Zenodo, Figshare) for repository/record sizes.
3. **Paper text parsing** (low confidence): Regex extraction of size mentions (e.g., "50 GB", "1.5 TB") near dataset-related keywords.

Use `scripts/estimate_size.py` to perform the estimation. See [references/estimate_size_usage.md](estimate_size_usage.md) for script usage.

### Confidence Levels

| Confidence | Condition |
|------------|-----------|
| `high` | Content-Length covers >80% of data URLs |
| `medium` | API estimates cover >50% of URLs, or partial Content-Length |
| `low` | Only paper text mentions available |
| `indeterminate` | No size information from any source |

### Pass Conditions

The paper passes Rule 3.6 when:
- Size can be estimated (confidence is not `indeterminate`), **AND**
- Estimated total size is ≤ 50 GB (tier is S or M)

### Reject Conditions

**Reject: Data Too Large**
- Estimated total size exceeds 50 GB (tier L)
- Evidence must include the estimated size and estimation source

**Reject: Size Indeterminate**
- No size information obtainable from any source (confidence is `indeterminate`)
- This means Content-Length is unavailable for all data URLs, platform APIs return no size information, and no size mentions found in paper text

### Judgment Method

1. Collect `file_size` values from Rule 3.1's `links_checked` results
2. Run `scripts/estimate_size.py` with the validate_links output and paper text
3. Record the estimation result (tier, confidence, per-URL estimates) in the filtering output
4. If tier is L or confidence is indeterminate → reject
5. If tier is S or M → pass, record `size_tier` in `task_info.data`

---

## Task Info Extraction

Fields extracted at this Level: `task_info.data.pattern`, `task_info.data.evaluation_settings[]` (only settings that **passed** Rule 3.5, each containing `d_dev` and `d_eval`), `task_info.data.rejected_settings[]` (settings that **failed** Rule 3.5, each with `name` and `failure_reason`), `task_info.data.setting_dependencies[]` (optional, only when cross-setting dependencies detected), `task_info.dependencies`, `task_info.data.size_tier`
