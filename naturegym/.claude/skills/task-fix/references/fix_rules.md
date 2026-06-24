# Fix Rules

Detailed fix strategies for each task-verify check. Organized by phase.

When fixing, always follow the **source of truth hierarchy** defined in SKILL.md. For task-build rules referenced below, consult the corresponding guide in `.claude/skills/task-build/references/`.

---

## Phase 0: File Completeness & Structure

### C0.1: Missing Required Files

**Files that may be missing**: `problem/README.md`, `problem/data_description.md`, `evaluation/evaluator.py`, `metadata.json`, `environment/Dockerfile.v3`, `environment/packages.json`

**Fix strategy**:

- **metadata.json missing**: Regenerate following task-build Phase 4 rules (metadata_guide.md). Read filter_result.json for task_info (metrics, domain, scores), README for task name and metric names, evaluator.py for metric consistency. Build the full metadata.json structure.
- **evaluator.py missing**: Regenerate following task-build Phase 3 rules (evaluator_guide.md). Read README Section 4-5 for metrics and output format, filter_result.json for metric definitions, ground_truth/ for reference data format. Follow the evaluator template. Run smoke test after generation.
- **README.md missing**: Regenerate following task-build Phase 2 rules (readme_guide.md). Read filter_result.json for task_info, data_description.md for data structure, paper for scientific context. Ensure all 6 sections are present.
- **data_description.md missing**: Regenerate following task-build Phase 1 rules (data_description_guide.md). Inspect actual files in problem/data/ to document structure, formats, and schemas.
- **Dockerfile missing**: Regenerate following task-build Phase 5 rules. Read evaluator.py imports and filter_result.json for required dependencies. Create Dockerfile inheriting from naturebench-base:v3 with only non-base dependencies added. Also generate `environment/packages.json` following `environment_guide.md` Step 4.
- **packages.json missing**: Regenerate following `environment_guide.md` Step 4. Read the existing Dockerfile to extract task packages and their import names. If `from_base` is true, copy base_packages from `references/base_packages.json`.

**Escalation**: Flag in `manual_review_needed` if regeneration requires information not available from existing sources. Still attempt generation with available information.

---

### C0.2: Instance Directory Mismatch

**Problem**: Directories in `problem/data/` don't match `evaluation/ground_truth/`.

**Fix strategy**:

1. List both directory sets
2. Determine the correct set by consulting filter_result.json's evaluation_settings and the paper
3. Cases:
   - **Extra dirs in problem/data/**: If no corresponding ground truth exists and cannot be created → remove the extra instance directory from problem/data/ and update all documents
   - **Extra dirs in ground_truth/**: If no corresponding problem data exists → remove the extra instance directory from ground_truth/
   - **Name mismatch**: If instances exist on both sides but with different names → determine correct name from filter_result.json, rename to match
4. After fixing directories, update all references: README Section 6 INSTANCES, evaluator.py INSTANCES, data_description.md, metadata.json performance_entries

**Caution**: Never delete data without confirming it's truly extraneous. If uncertain, flag for manual review.

---

### C0.3: metadata.json Invalid

**Problem**: metadata.json is not valid JSON, missing required fields, or has malformed structure.

**Fix strategy**:

- **Invalid JSON**: Read the file, identify syntax errors (trailing commas, missing quotes, unescaped characters), fix them
- **Missing `task_name`**: Extract from README first heading
- **Missing `performance_entries`**: Build from filter_result.json task_info.metrics and evaluation settings. Each instance gets one entry with all metrics listed
- **Missing `workflow_topology`**: Determine from filter_result.json task_info or paper context. Default to `strict_single_step` if unclear
- **Missing `methodology_paradigm`**: Determine from filter_result.json. Default to `general_ml_application` unless domain-specific tools are required
- **Missing `domain_metadata`**: Extract `primary_domain` from filter_result.json, infer `sub_domain` and `domain_tags` from paper context
- **Missing `compute_resource_requirements`**: Extract from filter_result.json or paper. If unavailable, set all severities to `medium` with `"estimated"` in quantity_text
- **Malformed `performance_entries`**: Ensure each entry has `dataset_name`, `metrics` array with `name`, `is_primary`, `metric_direction` fields

---

### C0.4: evaluator.py Syntax Error

**Problem**: Python syntax errors in evaluator.py.

**Fix strategy**:

1. Run `python -m py_compile evaluation/evaluator.py` to get the exact error
2. Read the file at the error location
3. Fix the syntax error (common: unclosed brackets, missing colons, indentation errors, unmatched quotes)
4. Re-run py_compile to verify

---

### C0.5: Dockerfile Dependency Viability Issues

**Problem**: Dockerfile packages conflict with base image, are unavailable on Python 3.11, are unpinned, are missing hard-requirement imports, or scripts use incompatible APIs for the installed library versions.

Follow the logic in `.claude/skills/task-build/references/environment_guide.md` (Step 2 per-package judgment + Script-First Rule + Handling Version Conflicts) to fix each issue.

**Fix strategy**:

1. **Package conflicts with base** (e.g., `tensorflow>=2.19.0` requires `numpy>=2.0`, but base has `numpy==1.26.4`):
   - Find a compatible version (e.g., `tensorflow>=2.16.0,<=2.18.x` which requires `numpy<2.0`). This is the preferred fix.
   - If no compatible version exists: override the conflicting base package with a comment, or use a standalone Dockerfile as a last resort.

2. **Package unavailable on Python 3.11** (e.g., `molsets==0.3.1` requires `pomegranate==0.12.0` which cannot build):
   - If a Tier 1/2 script imports it: **Script-First Rule** — fix the script to remove the dependency (substitute with an available alternative or re-implement), then remove the package from Dockerfile.
   - If Tier 3 paper dependency: find an alternative package. If none, omit with a comment.
   - If Tier 4 domain tool: omit with a comment.

3. **Missing hard imports** (Tier 1/2 import not satisfied by base + Dockerfile):
   - Identify the PyPI package that provides the import.
   - Add it to Dockerfile with a pinned compatible version.
   - If the package is not available: apply Script-First Rule on the importing script.

4. **Script API incompatibility** (e.g., script uses `np.float` removed in numpy 2.x):
   - **Script-First Rule** — fix the script's API calls to work with the installed version. Do NOT downgrade the library.
   - Common fixes: `df.append()` → `pd.concat()`.
   - Note: `np.float` → `float`, `np.int` → `int` are deprecated warnings in numpy 1.26.4 but still work — only fix if they cause actual errors.

5. **Unpinned versions**: Pin to a specific compatible version `==X.Y.Z`.

6. **Redundant base packages**: Remove from Dockerfile (or add a comment if intentionally overriding).

**Note**: Dockerfile is shared between evaluator and solver. All four dependency tiers (evaluator, solver scripts, paper core, domain tools) should be satisfied. See `environment_guide.md` for the full dependency classification.

**Sync packages.json**: After any Dockerfile modification (adding, removing, or changing package versions), update `environment/packages.json` accordingly to keep it consistent with the Dockerfile. Follow the format defined in `environment_guide.md` Step 4.

---

## Phase 1: Cross-File Consistency

### C1.1: Task Name Mismatch

**Problem**: Task name differs between README and metadata.json.

**Fix strategy**:

1. README heading is the source of truth (it's the user-facing document)
2. Extract task name from README first `#` heading
3. Update `task_name` field in metadata.json to match

---

### C1.2: Instance Names Inconsistent

**Problem**: Instance names don't match across README Section 6, data_description.md, metadata.json, evaluator.py, and actual directories.

**Fix strategy**:

1. **Source of truth**: `problem/data/` directory names (physical data)
2. List actual directories in `problem/data/`
3. Update all locations to match:
   - **README Section 6**: Update INSTANCES list in the run.py template code block
   - **evaluator.py**: Update INSTANCES list/variable
   - **data_description.md**: Update directory structure section and any instance references
   - **metadata.json**: Update `performance_entries[].dataset_name` to match
4. Also verify `evaluation/ground_truth/` directories match (fix C0.2 first if needed)

---

### C1.3: Metric Names Inconsistent

**Problem**: Metric names differ across README, metadata.json, and evaluator.py (case-sensitive).

**Fix strategy**:

1. **Determine canonical metric names**:
   - Check `filter_result.json` → `task_info.metrics[].name` for the original names
   - Check the paper for how metrics are written (e.g., "RMSE" vs "rmse" vs "Root Mean Square Error")
   - Prefer the form used in the paper/filter_result.json
2. **Update all three locations** to use the canonical name:
   - **README Section 4**: Metric names in definitions
   - **evaluator.py**: `METRIC_NAMES` list/variable AND metric keys in returned dictionaries
   - **metadata.json**: `performance_entries[].metrics[].name`
3. **Verify**: After fixing, confirm all three locations have identical metric name sets

**Common patterns**:
- Case mismatch: "RMSE" vs "rmse" → use paper's casing
- Abbreviation vs full name: "MAE" vs "Mean Absolute Error" → use the abbreviated form as the metric key, full name in description only
- Extra/missing metrics: One location has metrics the others don't → align to what the paper actually evaluates

---

### C1.4: Metric Direction Mismatch

**Problem**: Metric direction (higher_is_better / lower_is_better) conflicts between README and metadata.json.

**Fix strategy**:

1. Determine correct direction from the paper and filter_result.json
2. Common directions:
   - **higher_is_better**: Accuracy, AUC, R², F1, Precision, Recall, SSIM, PSNR
   - **lower_is_better**: RMSE, MAE, MSE, Loss, FID, Perplexity, Error Rate
3. Update the incorrect location:
   - README Section 4: Update "Higher/Lower is better" text
   - metadata.json: Update `performance_entries[].metrics[].metric_direction`

---

### C1.5: Primary Metric Issue

**Problem**: Zero or multiple primary metrics designated in README Section 4.

**Fix strategy**:

1. Check filter_result.json → `task_info.metrics` to see which metric is considered primary (usually the first one listed, or explicitly marked)
2. If the paper clearly designates a primary metric, use that
3. **Zero primary**: Add "Primary Metric" designation to the correct metric in README Section 4
4. **Multiple primary**: Keep only one as primary, move others to "Other Metrics" subsection
5. Update metadata.json: Ensure exactly one metric has `"is_primary": true`

---

### C1.6: Output Format Mismatch

**Problem**: Output format in README Section 5 doesn't match what evaluator.py expects.

**Fix strategy**:

1. **README Section 5 is the specification** — it defines what solvers should produce
2. Read evaluator.py's loading logic (file name, format, shape expectations)
3. Determine which is correct by consulting filter_result.json and paper
4. Cases:
   - **Filename mismatch**: e.g., README says `output.npy`, evaluator loads `predictions.npy` → align evaluator to README (or vice versa if README is clearly wrong)
   - **Format mismatch**: e.g., README says CSV, evaluator loads NPY → fix the incorrect one
   - **Shape/dtype mismatch**: e.g., README says `(n_samples,)`, evaluator expects `(n_samples, 1)` → align to what ground truth actually is
5. After fixing, update the Output Format table in README Section 5 and/or evaluator.py's `load_and_validate` function

---

### C1.7: Ground Truth Paths Don't Exist

**Problem**: evaluator.py references ground truth files that don't exist at the specified paths.

**Fix strategy**:

1. Read evaluator.py to find all ground truth path references
2. List actual files in `evaluation/ground_truth/` for each instance
3. Cases:
   - **Path pattern wrong**: e.g., evaluator uses `ground_truth/{instance}/labels.npy` but file is `ground_truth/{instance}/y_test.npy` → update evaluator.py path references
   - **Instance name in path wrong**: e.g., evaluator uses `ground_truth/dataset_1/` but dir is `ground_truth/setting_1/` → update evaluator.py (cascading from C1.2 fix)
   - **File genuinely missing**: Flag for manual review — ground truth cannot be auto-generated

---

### C1.8: data_description.md Directory Structure Mismatch

**Problem**: Directory tree in data_description.md Section 1 doesn't match actual files in `problem/data/`.

**Fix strategy**:

1. List all actual files recursively under `problem/data/`
2. Regenerate the directory structure section in data_description.md:
   - Use tree-style format with inline annotations
   - Include file counts/sizes as comments where helpful
   - Follow task-build data_description_guide.md formatting rules
3. If new files exist that weren't documented, add descriptions for them
4. If files were documented but don't exist, remove those entries
5. Preserve all other sections of data_description.md unchanged

---

### C1.9: data_description.md Missing Required Sections

**Problem**: data_description.md missing one or more of the 4 required sections (Directory Structure, Dataset Overview, File Formats & Schemas, Special Notes).

**Fix strategy**:

1. Identify which section(s) are missing
2. Generate the missing section(s) following task-build data_description_guide.md:
   - **Directory Structure**: Generate tree view from actual `problem/data/` contents
   - **Dataset Overview**: Write 1-3 paragraphs summarizing the data from filter_result.json and actual file inspection
   - **File Formats & Schemas**: Inspect actual files to document formats, columns, dtypes, shapes
   - **Special Notes**: Add any data-level caveats (e.g., missing values, encoding, scale). If none, write "None."
3. Insert in correct position (numbered 1-4)

---

## Phase 2: Information Firewall

### C2.1 / C2.2: Paper References in README / data_description.md

**Problem**: Paper references found (DOI, author citations, attribution phrases, or journal names used in a bibliographic context).

**Fix strategy**:

1. Read the `issue` field to find the exact matched text and line number
2. Read the surrounding context in the file
3. **High-confidence matches** (DOI, "et al.", explicit attribution phrases) → always fix:
   - "The authors propose..." → "The task requires..." or "The objective is..."
   - "et al." references → remove the sentence or rephrase without attribution
   - DOI patterns / arXiv IDs → remove entirely
4. **Context-dependent matches** (journal names, "this study", "the paper") → verify before fixing:
   - If the match is a domain term (e.g., "cell type", "nature of the problem") → **not a violation, do not modify**
   - If the match is genuinely bibliographic (e.g., "published in Cell", "Nature 2023") → remove or replace with "published research"
   - "this study" describing the data source factually → may be acceptable; rephrase only if it attributes a contribution to the paper's authors
5. Ensure the replacement maintains the paragraph's meaning and flow
6. Do NOT simply delete sentences if they contain important scientific context — rephrase them in task-centric language

---

### C2.3 / C2.4: Algorithm Names in README / data_description.md

**Problem**: Algorithm name from filter_result.json found in solver-visible documents.

**Fix strategy**:

1. Read filter_result.json → `task_info.algorithm` to get the algorithm name
2. Find all occurrences in the target file
3. For each occurrence, read the surrounding context to understand what it conveys. Don't just swap the name for a generic term — if the surrounding text describes the algorithm's approach or architecture, that description itself is also a leak. Rewrite the passage in task-centric language that describes the problem and data without revealing the method.
4. After modifications, re-read the affected paragraphs to verify coherence
5. Scan for common variants: abbreviations, lowercase/uppercase forms, partial matches

---

### C2.5: Prescriptive Method Guidance in README

**Problem**: README contains prescriptive method guidance — directives to use specific architectures, hyperparameter values, or training procedures.

**Fix strategy**:

1. Read the matched text and surrounding context
2. Apply the same disambiguation as verification — determine if the match is truly prescriptive:
   - **Data-grounded reference** (model file exists in `problem/data/`): Not a violation — do not modify
   - **Domain vocabulary** ("cell type", "attention span", "transformer station"): Not a violation — do not modify
   - **Prescriptive architecture directive** ("use ResNet-50", "apply a Transformer"): Remove or generalize to task-level language ("develop a model that predicts...")
   - **Specific hyperparameter values** ("learning rate of 0.001", "train for 50 epochs"): Remove entirely — solvers should choose their own
   - **Training procedure instructions** ("use Adam optimizer", "apply cosine annealing"): Remove — README should describe the task, not how to solve it
3. When removing prescriptive text, do not replace with vague method hints. Either remove the sentence entirely or rewrite it to describe the task objective instead

---

### C2.6: References to Evaluation Directory Structure

**Problem**: README or data_description.md reveals evaluation system internals (directory paths, hidden test data structure).

**Fix strategy**:

1. Find and remove or rephrase the reference
2. Common replacements:
   - "evaluation/" or "evaluation/ground_truth/" → remove the path reference entirely
   - "hidden test set" → "test set" (the hiding is implicit)
   - "held-out test set" (when referring to evaluator-side data) → "test set"
   - "the evaluator will..." → remove (solver shouldn't know evaluator internals)
3. **Allowed terminology** (standard ML terms, do NOT remove):
   - "ground truth" (as a general term for correct labels/answers)
   - "true labels", "correct answers", "reference values"
   - "gold standard", "oracle", "target values"
4. Ensure no sentence implies the existence of hidden data that gives away evaluation structure

---

## Phase 3: Benchmark Design Principles

### C3.1: Missing Initial Data

**Problem**: Training or validation data missing from problem/data/.

**Fix strategy**:

1. Read data_description.md and filter_result.json to understand expected data structure
2. Check if data exists elsewhere (e.g., in the paper folder's `data/` directory before reorganization)
3. If data was missed during task-build Phase 0 reorganization → copy from source
4. If data genuinely doesn't exist → flag for `manual_review_needed`
5. After adding data, update data_description.md directory structure

**Escalation**: This often requires human intervention. Flag clearly with what data is expected.

---

### C3.2: Algorithm Artifacts in problem/data/

**Problem**: Algorithm outputs, logs, checkpoints, or cache files found in problem/data/.

**Fix strategy**:

Delete artifacts following the pattern whitelist from task-build data_organization_guide:

- `results/`, `outputs/`, `predictions/` directories → delete
- `logs/`, `*.log` → delete
- `checkpoints/`, `*.ckpt`, `*.pth`, `*.h5` → delete **unless** explicitly identified as pretrained models in filter_result.json
- `__pycache__/`, `*.pyc`, `.cache/` → delete
- Experiment config files that reference algorithm A → delete

After deletion, update data_description.md to remove references to deleted files.

---

### C3.3: Missing README Sections

**Problem**: README missing one or more of the 6 required sections.

**Required sections**: Scientific Problem, Task Objective, Dataset Information, Evaluation Metrics, Output Format, Submission Guidelines

**Fix strategy**:

1. Identify which section(s) are missing
2. Generate the missing section(s) following task-build readme_guide.md:
   - **Scientific Problem**: Write 1-2 paragraphs of scientific background from the paper (via preprocessed/text.md), maintaining information firewall
   - **Task Objective**: Define ML objective with Input/Output specification from filter_result.json task_info
   - **Dataset Information**: Brief description from data_description.md
   - **Evaluation Metrics**: From filter_result.json task_info.metrics — define primary and other metrics with direction
   - **Output Format**: From filter_result.json and evaluator.py — filename, format, shape, dtype, value constraints
   - **Submission Guidelines**: run.py template with INSTANCES list from filesystem, data loading example
3. Insert in the correct position (numbered 1-6)
4. Ensure consistency with existing sections

---

### C3.4: Incomplete Output Format Specification

**Problem**: README Section 5 missing filename, format, shape, dtype, or value constraints.

**Fix strategy**:

1. Read evaluator.py to determine what it expects (file loading logic, validation logic)
2. Read ground truth files to infer format details (shape, dtype)
3. Read filter_result.json for any output format information
4. Add missing details to the Output Format table in README Section 5:
   - **Filename**: from evaluator.py's OUTPUT_FILE or loading path
   - **Format**: from file extension and evaluator loading function (np.load → NPY, pd.read_csv → CSV, etc.)
   - **Shape**: from ground truth file shape or evaluator validation
   - **Dtype**: from ground truth file dtype or evaluator validation
   - **Value constraints**: from evaluator validation logic (e.g., `assert np.all(pred >= 0)` → "non-negative") or task nature (classification → integer labels, probability → [0,1])

---

### C3.5: Missing INSTANCES List in Submission Guidelines

**Problem**: README Section 6 has empty, placeholder, or missing INSTANCES list.

**Fix strategy**:

1. List actual instance directories in `problem/data/`
2. Update the INSTANCES list in the run.py template code block in Section 6
3. Ensure the code template includes:
   - Correct `DATA_DIR` and `OUTPUT_DIR` environment variables
   - Populated INSTANCES list
   - Data loading example for the first instance
   - Output saving example matching Section 5 format

---

### C3.6: Missing SOTA Scores

**Problem**: Metrics in README lack SOTA scores (paper's proposed method) in metadata.json.

**Fix strategy**:

1. Read filter_result.json → `task_info.metrics[].score_source` to find where scores are reported in the paper
2. Locate the score source:
   - **First, search preprocessed/text.md**: Look for the referenced table/figure number. Many tables are converted to markdown format in text.md. If found and scores are readable, extract from there.
   - **If not in text.md or unclear, check image files**: Look in `preprocessed/figures/` or `preprocessed/tables/` for the corresponding image file and extract visually.
   - **Supplementary materials**: If `score_source` references supplementary content (e.g., "Supplementary Table S3", "SI Figure 2"):
     - Check if preprocessed/text.md already includes supplementary content (some preprocessing pipelines merge it)
     - If not included, check `preprocessed/links.json` for supplementary material links (section: `supplementary_information`)
     - Download supplementary PDF/files to temporary location if needed
     - Extract the referenced table/figure
     - Delete downloaded files after extraction
3. Extract scores:
   - **From tables**: Exact values including variance (e.g., "95.5 ± 0.2")
   - **From figures**: Approximate values with `~` prefix (e.g., "~0.85")
   - Include method name (e.g., "LinearRegression: 0.89", "Random Forest: 0.92")
4. Add to metadata.json → `performance_entries[].metrics[].sota_score` and/or `baseline_score`
5. If scores cannot be found in any source → set to `null` and add a note in the fix log

---

### C3.7: Oracle/Scorer Placement and Originality Issues

**Problem**: Missing Oracle components on solver/evaluator side, or Oracle .py files are direct copies from repository.

**Fix strategy**:

**Placement issues**:
1. Identify what Oracle components are needed (from README and filter_result.json)
2. If solver side missing Oracle → copy/generate Oracle components to `problem/data/{instance}/`
3. If evaluator side missing Oracle → copy/generate Oracle components to `evaluation/` (in ground_truth/, shared/, or inline in evaluator.py)
4. Pure library Oracles (e.g., RDKit) → ensure Dockerfile includes the library

**Originality issues** (`.py` files or inlined metric functions appear copied from repository):
1. Read the original repository file and the task package copy (standalone script or evaluator.py functions)
2. Identify which functions are actually needed for evaluation — delete everything unrelated
3. Re-implement the remaining functions: rewrite without closely mirroring the original (different code structure, variable naming; prefer standard library equivalents where available)
4. Fix any library compatibility issues (deprecated APIs, version-specific calls)
5. Remove original copyright/license headers
6. Verify the re-implemented code produces equivalent outputs on shared test inputs

**Escalation**: Complex Oracle re-implementation may need manual review. Flag if the domain logic is too specialized.

**Script usability issues** (unresolved imports, hardcoded paths, syntax errors, version incompatibility in any `.py` script):
1. Fix unresolved imports: update to library versions available in the Dockerfile, or add missing dependencies to Dockerfile
2. Fix version-incompatible API calls: check `environment/Dockerfile.v3` and base image (`.claude/skills/task-build/references/Dockerfile.base.v3`) for pre-installed library versions, then update deprecated/removed function calls, renamed parameters, or changed return types to match the target environment versions
3. Replace hardcoded repository paths with relative paths matching the task package structure
4. Fix syntax errors

---

## Phase 4: Dynamic Testing

Phase 4 fixes are the most complex because they involve runtime behavior. The general approach is: diagnose → fix → re-test.

### C4.1: Baseline Solver Generation Failed

**Problem**: Could not generate a functional baseline solver.

**Fix strategy**: This is task-verify's internal issue, not a task package issue. Skip — the task-fix skill will generate its own baseline solver in Phase 4 of the workflow.

---

### C4.2: Baseline Solver Execution Failed

**Problem**: Baseline solver crashed or timed out.

**Fix strategy**:

The baseline solver is auto-generated by task-verify — failures may be the baseline's own bug rather than a task package issue. Before modifying the package, check whether the error originates from the baseline code itself or from a genuine package problem (wrong documentation, missing data, missing dependencies).

1. Read the error message from task_verify_result.json
2. If the error is clearly in the baseline's own logic (e.g., wrong indexing, misused API) and README/evaluator/data are internally consistent → not a package issue
3. If the error points to package inconsistencies (documentation doesn't match actual data, missing files, missing Dockerfile dependencies) → fix the package
4. Re-run dynamic test after any package fixes

---

### C4.3: Output File Validation Failed

**Problem**: Baseline solver output doesn't match README specification.

**Fix strategy**:

Same principle — distinguish between a baseline implementation bug and a package inconsistency.

1. Check if README Section 5 and evaluator.py agree on the expected output format
2. If they agree, the baseline likely just produced wrong output → not a package issue
3. If they disagree, determine which is correct by consulting ground truth format and paper, then fix the incorrect one
4. Common package issues to fix: filename mismatch between README and evaluator, shape/dtype inconsistency, format specification that doesn't match actual data

---

### C4.4: Evaluator Execution Failed

**Problem**: evaluator.py crashed or timed out when scoring baseline outputs.

**Fix strategy**:

1. Read the error message carefully
2. Common causes and fixes:
   - **Import error**: Missing dependency → add to `environment/Dockerfile.v3`. Note: Dockerfile is shared with solver, consider whether changes could affect solver side.
   - **File path error**: Ground truth path wrong → fix path in evaluator.py (see C1.7)
   - **Type/shape error in scoring**: Evaluator assumes wrong format → fix evaluator.py scoring logic to match actual ground truth and output format
   - **Division by zero or NaN**: Edge case in metric computation → add safe handling
   - **Timeout**: Metric computation too slow → optimize or flag for review
3. After fixing evaluator.py, verify syntax: `python -m py_compile evaluation/evaluator.py`
4. Re-run dynamic test

---

### C4.5: Evaluator Output Structure Wrong

**Problem**: score.json missing instances or metrics, or has wrong structure.

**Fix strategy**:

1. Check evaluator.py's output writing logic
2. Ensure it produces the correct structure: `{"instance_name": {"MetricName": value, ...}, ...}`
3. Common issues:
   - **Missing instances**: INSTANCES list in evaluator doesn't match actual instances → fix INSTANCES (see C1.2)
   - **Missing metrics**: Evaluator doesn't compute all metrics → add missing metric computation
   - **Wrong metric names in output**: Metric keys don't match METRIC_NAMES → fix the return dict keys
   - **Averaged instead of per-instance**: Evaluator returns averaged scores → fix to return per-instance dicts
4. Ensure score.json is written to the correct location (evaluator's working directory)

---

### C4.6: Suspicious Scores

**Problem**: Scores are NaN, Inf, negative when should be positive, or suspiciously perfect.

**Fix strategy** (warning level):

1. Read the specific score values and metrics
2. Common causes:
   - **NaN/Inf**: Division by zero, log of zero, empty arrays → add guards in evaluator.py
   - **Negative score for normally positive metric**: Sign error in evaluator → fix computation
   - **Perfect score on random baseline**: Evaluator bug (e.g., comparing output to itself instead of ground truth) → fix evaluator logic
   - **Score outside expected range**: Metric computation error → verify formula against paper
3. If scores are genuinely bad but valid (random baseline gets low scores) → this is expected, not an issue

---

### C4.7: Interface Conformance Issue

**Problem**: Baseline solver doesn't conform to README Section 6 interface specification.

**Fix strategy**: This is typically a task-verify baseline generation issue, not a task package issue. However, check:

1. Is the run.py template in README Section 6 well-formed?
2. Does it have `main()` function, `DATA_DIR`, `OUTPUT_DIR`, and `INSTANCES` defined?
3. Does it have `if __name__ == "__main__": main()` pattern?
4. Does INSTANCES match actual instances?
5. If the template is malformed → fix README Section 6 to include correct template following readme_guide.md (main() function pattern, not Solution class)

---

### C4.8: Evaluator Correctness — Ground Truth Test Failed

**Problem**: Evaluator produces wrong scores when given ground truth as perfect prediction input, indicating a bug in the scoring logic.

**Fix strategy**:

1. Read the error message to identify which metric(s) scored incorrectly and what scores were produced
2. Read evaluator.py's `calculate_metrics()` function carefully
3. Common causes and fixes:
   - **Flipped metric direction**: e.g., computing `1 - accuracy` instead of `accuracy`, or negating a correlation → fix the formula
   - **Wrong normalization**: e.g., dividing by wrong count, or not averaging correctly → fix denominator/aggregation
   - **Off-by-one**: e.g., using `len(x) - 1` instead of `len(x)` → fix the index or count
   - **Incorrect formula**: e.g., MAE formula computing MSE instead → verify formula against standard definition and paper
   - **Type casting error**: e.g., integer division truncating results → ensure float division
   - **Wrong ground truth loading**: evaluator loads ground truth incorrectly (wrong column, wrong file) → fix `load_ground_truth()` paths and parsing
   - **Comparison against wrong reference**: e.g., comparing predictions to predictions instead of ground truth → fix variable references in `calculate_metrics()`
4. After fixing, re-run the ground truth test to verify near-perfect scores
5. Also re-run baseline test (C4.2–C4.6) to verify baseline still works

**Note**: If the task is Oracle-type and C4.8 was skipped in verification, this check won't appear in task_verify_result.json.

---

### C4.9: Evaluator Robustness — Malformed Input Test Failed

**Problem**: Evaluator silently produces numeric scores or crashes with unhandled exceptions when given malformed solver outputs.

**Fix strategy**:

1. Read which malformed input cases failed and what the evaluator did wrong
2. Fix evaluator.py's `load_and_validate()` function to add validation for each failing case:

   | Failed Case | Validation to Add |
   |------------|-------------------|
   | Missing file | Check `os.path.exists(pred_file)` before loading; raise `ValidationError` if missing |
   | Empty file | Check `os.path.getsize(pred_file) > 0` after existence check |
   | Wrong format | Wrap file loading in try/except; catch format-specific errors (e.g., `pd.errors.ParserError`, `ValueError` from `np.load`) |
   | Invalid values (NaN/Inf) | After loading: `if np.any(np.isnan(predictions)) or np.any(np.isinf(predictions)): raise ValidationError(...)` |
   | Wrong sample count | After loading: compare `len(predictions)` to expected count (from ground truth or known constant); raise if mismatch |
   | Misaligned IDs | After loading: compare prediction IDs against ground truth IDs; raise if not matching sets |

3. Ensure validation errors are caught by the `try/except` block in `run_evaluation()` and routed to `error_result()` — NOT allowed to crash the evaluator
4. Pattern to follow:
   ```python
   try:
       predictions = load_and_validate(instance_name)
       # ... scoring ...
   except ValidationError as e:
       results[instance_name] = error_result(f"Validation: {e}")
   except Exception as e:
       results[instance_name] = error_result(e)
   ```
5. After fixing, re-run the robustness test to verify all 6 cases now produce error_result or clean exit

**Severity guidance**:
- `false_scores` (evaluator silently accepts garbage) → **must fix** — this is a correctness bug
- `crash` (unhandled exception) → **should fix** — add try/except handling. If the crash is from a warning in task_verify_result.json, still fix to improve robustness

---

## Cross-Cutting Fix Patterns

### Cascading Fixes

Some fixes naturally resolve multiple checks. Track these to avoid redundant work:

| Primary Fix | May Also Resolve |
|------------|-----------------|
| C1.2 (instance names) | C4.5 (score structure), C4.7 (interface) |
| C1.3 (metric names) | C4.5 (score structure) |
| C1.6 (output format) | C4.3 (output validation) |
| C1.7 (ground truth paths) | C4.4 (evaluator failure) |
| C0.4 (syntax error) | C4.4 (evaluator failure) |
| C4.8 (evaluator correctness) | C4.6 (suspicious scores) |
| C4.9 (evaluator robustness) | C4.4 (evaluator failure) |

### Iterative Consistency

After any fix that modifies metric names, instance names, or output format, immediately check all related files for consistency. The interconnected files are:

- **Metric names**: README Section 4 ↔ evaluator.py METRIC_NAMES ↔ metadata.json performance_entries
- **Instance names**: README Section 6 ↔ evaluator.py INSTANCES ↔ data_description.md ↔ metadata.json ↔ filesystem
- **Output format**: README Section 5 ↔ evaluator.py load_and_validate ↔ evaluator.py scoring logic

### File Regeneration Guidelines

When regenerating a file entirely (C0.1 cases), follow these task-build references:

| File | Task-Build Phase | Reference Guide |
|------|-----------------|-----------------|
| `problem/data_description.md` | Phase 1 | `.claude/skills/task-build/references/data_description_guide.md` |
| `problem/README.md` | Phase 2 | `.claude/skills/task-build/references/readme_guide.md` |
| `evaluation/evaluator.py` | Phase 3 | `.claude/skills/task-build/references/evaluator_guide.md` |
| `metadata.json` | Phase 4 | `.claude/skills/task-build/references/metadata_guide.md` |
| `environment/Dockerfile.v3` | Phase 5 | `.claude/skills/task-build/references/environment_guide.md` |

Always read the relevant guide before regenerating. The guide defines the structure, required content, and constraints.
