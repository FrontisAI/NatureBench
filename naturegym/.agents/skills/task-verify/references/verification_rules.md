# Verification Rules

This document defines all 34 verification checks in detail.

## Phase 0: File Completeness & Structure

### C0.1: Required Files Exist

**What to verify**: All essential files are present in the task package.

**Required files**:
- `problem/README.md`
- `problem/data_description.md`
- `evaluation/evaluator.py`
- `metadata.json`
- `environment/Dockerfile.v3`
- `environment/packages.json`

**How to verify**: Use file existence checks.

**Pass criteria**: All 6 files exist.

**Fail criteria**: Any file is missing.

**Error message format**: `"Missing required file: {file_path}"`

---

### C0.2: Instance Directories Match

**What to verify**: Instance directories in problem/data/ match those in evaluation/ground_truth/.

**How to verify**:
1. List directories in `problem/data/`
2. List directories in `evaluation/ground_truth/`
3. Compare the two sets

**Pass criteria**: Sets are identical (same instance names).

**Fail criteria**: Mismatch in instance names.

**Error message format**:
- `"Instances in problem/data/ but not in evaluation/ground_truth/: {missing}"`
- `"Instances in evaluation/ground_truth/ but not in problem/data/: {extra}"`

---

### C0.3: metadata.json Valid JSON with Required Fields

**What to verify**: metadata.json is valid JSON and contains required fields with correct types.

**Required top-level fields**:
- `task_name` (string)
- `workflow_topology` (string, one of: `strict_single_step`, `serial_pipeline`, `multi_task_parallel`, `pretrain_finetune`)
- `methodology_paradigm` (string, one of: `domain_specific_tooling`, `general_ml_application`, `other`)
- `tooling_metadata` (object if methodology_paradigm == "domain_specific_tooling", else null)
- `domain_metadata` (object with required keys: `primary_domain`, `sub_domain`, `domain_tags`)
- `compute_resource_requirements` (object with required keys: `cpu_compute`, `gpu_compute`, `runtime`)
- `performance_entries` (array, non-empty)

**Required performance_entries[] fields**:
- `dataset_name` (string)
- `metrics` (array, non-empty, each with: `name`, `is_primary`, `metric_direction`)

**How to verify**:
1. Parse metadata.json as JSON
2. Check for all required top-level fields and types
3. Validate domain_metadata sub-fields exist
4. Validate compute_resource_requirements sub-fields exist
5. Validate each performance_entry has required fields

**Pass criteria**: Valid JSON with all required fields present and correctly typed.

**Fail criteria**: Invalid JSON or missing/malformed required fields.

**Error message format**:
- `"metadata.json is not valid JSON: {error}"`
- `"metadata.json missing required field: {field}"`
- `"metadata.json field '{field}' has invalid type: expected {expected}, got {actual}"`
- `"metadata.json performance_entries[{i}] missing required field: {field}"`

---

### C0.4: evaluator.py Valid Python Syntax

**What to verify**: evaluator.py has valid Python syntax.

**How to verify**: Use `python -m py_compile evaluation/evaluator.py`

**Pass criteria**: No syntax errors.

**Fail criteria**: Syntax errors detected.

**Error message format**: `"evaluator.py has syntax errors: {error}"`

---

### C0.5: Dockerfile Dependency Viability

**What to verify**: `environment/Dockerfile.v3` provides a viable execution environment — all packages are installable on Python 3.11, compatible with the base image, and scripts use APIs available in the installed versions.

**How to verify**:

Follow the analysis logic in `.claude/skills/task-build/references/environment_guide.md` Step 1-2 (collect dependencies → per-package judgment), applied as a read-only audit:

1. **Collect all required packages** using the four-tier model:
   - Tier 1: evaluator imports from `evaluation/*.py`
   - Tier 2: solver-side script imports from `problem/data/**/*.py`
   - Tier 3: `filter_result.json` → `task_info.dependencies`
   - Tier 4: domain-common tools (based on task type)
   - Note: imports inside `try/except ImportError` blocks are optional — they have fallback paths

2. **Check each Dockerfile package against the base image** (`Dockerfile.base.v3`):
   - Is the package already in base? → redundant (warning)
   - Is the package pinned to a specific version? → unpinned is a warning
   - Is the pinned version compatible with base packages (especially numpy, torch, scipy)? → conflict is a fail
   - Is the package available on PyPI for Python 3.11? → unavailable is a fail
   - Known conflicts to check:
     - `tensorflow>=2.19.0` requires `numpy>=2.0` (base has `numpy==1.26.4`) → fail; use `tensorflow>=2.16.0,<=2.18.x` instead
     - `molsets==0.3.1` requires `pomegranate==0.12.0` (cannot build on Python 3.11) → fail
     - Packages depending on `rdkit-pypi` (old package name, may conflict with base `rdkit`) → fail
     - Any package with `Requires-Python: <3.11` → fail

3. **Check for missing dependencies**:
   - Are there Tier 1/2 imports (hard requirements) that are NOT satisfied by base + Dockerfile packages? → fail
   - Are there Tier 3 paper dependencies missing from both base and Dockerfile? → warning

4. **Check script API compatibility**:
   - Do scripts use deprecated/removed APIs for the versions in base or Dockerfile?
   - numpy 1.x (base is 1.26.4): `np.bool`, `np.int`, `np.float` etc. are deprecated but still work — NOT a fail. However, code using numpy 2.x-only APIs will fail.
   - pandas 2.x removals: `DataFrame.append()`
   - API incompatibility in evaluator/solver scripts → fail

**Pass criteria**: All Dockerfile packages are installable, compatible with base, pinned; all hard imports (Tier 1/2) are satisfied; no API incompatibilities detected in scripts.

**Fail criteria**: Package conflicts with base, package unavailable on Python 3.11, hard import not satisfied, script API incompatible with installed version.

**Warning criteria**: Unpinned versions, redundant base packages, missing Tier 3 dependencies.

**Error/Warning message format**:
- `"Dockerfile package '{pkg}=={ver}' conflicts with base: {detail}"`
- `"Dockerfile package '{pkg}' not available on PyPI for Python 3.11"`
- `"Hard import '{module}' (from {file}) not satisfied by base + Dockerfile packages"`
- `"Script '{file}' uses deprecated API: {detail} (incompatible with {pkg}=={ver})"`
- `"Dockerfile package '{pkg}' not pinned to a specific version"`
- `"Dockerfile package '{pkg}' already in base image (redundant)"`
- `"Tier 3 dependency '{pkg}' not in base or Dockerfile"`
- `"packages.json task_packages out of sync with Dockerfile: {detail}"`

**Additional check — packages.json consistency**:
5. **Verify packages.json matches Dockerfile**:
   - Every package in the Dockerfile's `pip install` lines should have a corresponding entry in `packages.json` `task_packages`
   - Every entry in `packages.json` `task_packages` should correspond to a package in the Dockerfile
   - Versions should match
   - If `from_base` is `true`, verify the Dockerfile uses `FROM naturebench-base:v3`
   - Mismatches → warning (packages.json is a derived artifact; the Dockerfile is the source of truth)

---

## Phase 1: Cross-File Consistency

### C1.1: Task Name Matches

**What to verify**: Task name is consistent between README and metadata.json.

**How to verify**:
1. Extract task name from README (typically first heading or from Section 1)
2. Read `task_name` from metadata.json
3. Compare (case-insensitive, ignore minor punctuation differences)

**Pass criteria**: Names match semantically.

**Warning criteria**: Names are clearly different. (This is cosmetic — a name mismatch does not break solver, evaluator, or scoring.)

**Warning message format**: `"Task name mismatch: README has '{readme_name}', metadata.json has '{metadata_name}'"`

---

### C1.2: Instance Names Consistent

**What to verify**: Instance names are consistent across all locations.

**Locations to check**:
1. README Section 6 (INSTANCES list in code template)
2. data_description.md (directory structure section)
3. metadata.json (performance_entries[].dataset or similar field)
4. evaluator.py (INSTANCES variable)
5. Actual directories in problem/data/

**How to verify**: Extract instance names from each location and compare.

**Pass criteria**: All locations have identical instance name sets.

**Fail criteria**: Any mismatch.

**Error message format**: `"Instance names inconsistent: README has {readme_instances}, evaluator.py has {eval_instances}, actual directories have {dir_instances}"`

---

### C1.3: Metric Names Consistent

**What to verify**: Metric names are consistent across README, metadata, and evaluator.

**Locations to check**:
1. README Section 4 (Evaluation Metrics)
2. metadata.json (performance_entries[].metrics[].name)
3. evaluator.py (METRIC_NAMES variable or metric computation function names)

**How to verify**: Extract metric names from each location and compare (case-sensitive).

**Pass criteria**: All locations have identical metric name sets.

**Fail criteria**: Any mismatch in names or casing.

**Error message format**: `"Metric names inconsistent: README has {readme_metrics}, metadata has {metadata_metrics}, evaluator has {eval_metrics}"`

**Location format**: Include file paths and line numbers where metrics are defined.

---

### C1.4: Metric Directions Match

**What to verify**: Metric direction (higher/lower is better) matches between README and metadata.

**How to verify**:
1. Extract metric directions from README Section 4
2. Extract metric directions from metadata.json (performance_entries[].metrics[].direction)
3. Compare for each metric

**Pass criteria**: Directions match for all metrics.

**Fail criteria**: Any metric has conflicting directions.

**Error message format**: `"Metric direction mismatch for '{metric}': README says '{readme_dir}', metadata says '{metadata_dir}'"`

---

### C1.5: Exactly One Primary Metric

**What to verify**: README designates exactly one primary metric.

**How to verify**: Look for "primary metric" designation in README Section 4.

**Pass criteria**: Exactly one metric is marked as primary.

**Fail criteria**: Zero or multiple primary metrics.

**Error message format**:
- `"No primary metric designated in README Section 4"`
- `"Multiple primary metrics designated: {metrics}"`

---

### C1.6: Output Format Matches Evaluator

**What to verify**: Output format specification in README Section 5 matches what evaluator.py expects to load.

**How to verify**:
1. Extract output format from README Section 5 (filename, format, structure)
2. Analyze evaluator.py to find file loading logic
3. Check if they match

**Pass criteria**: Evaluator loads files matching README specification.

**Fail criteria**: Mismatch in filename, format, or structure.

**Error message format**: `"Output format mismatch: README specifies '{readme_format}', but evaluator expects '{eval_format}'"`

**Location format**: Include README section and evaluator.py line numbers.

---

### C1.7: Ground Truth Paths Exist and Non-Empty

**What to verify**: All ground truth files referenced by evaluator.py actually exist and are non-empty.

**How to verify**:
1. Parse evaluator.py to find all ground truth file paths it loads
2. Check if each referenced path exists
3. Check if each file has size > 0

**Pass criteria**: All referenced ground truth files exist and are non-empty.

**Fail criteria**: Any referenced file is missing or empty.

**Error message format**:
- `"Ground truth path referenced in evaluator.py does not exist: {path} (referenced at evaluator.py:{line})"`
- `"Ground truth file is empty: {path}"`

**Note**: This is evaluator-driven. If ground_truth/ contains extra files the evaluator doesn't use, that's not a failure. If the evaluator scores via an Oracle/scorer without reading ground_truth files, this check passes trivially.

---

### C1.8: data_description Directory Structure Matches Actual Files

**What to verify**: The directory tree shown in Section 1 of `data_description.md` accurately represents the actual contents of `problem/data/`. This is a bidirectional check: every file described must exist on disk, and every file on disk must be described.

**How to verify**:
1. Parse the code block under `## 1. Directory Structure` in `data_description.md`
2. Extract file/directory paths from the tree (ignore inline comments like `# 800 lines`)
3. List all actual files recursively under `problem/data/`
4. Compare both directions: described-but-absent, and present-but-undescribed

**Pass criteria**: One-to-one correspondence between described and actual files.

**Fail criteria**: Any file described but missing on disk, or any file present on disk but not described.

**Error message format**:
- `"data_description.md describes file not found on disk: {path}"`
- `"File exists in problem/data/ but not described in data_description.md: {path}"`

---

### C1.9: data_description.md Has Required Sections

**What to verify**: data_description.md follows the standard section structure defined by task-build.

**Required structure**:
1. `# Data Description` — top-level heading (H1)
2. `## 1. Directory Structure` — must contain a code block with directory tree
3. `## 2. Dataset Overview` — prose description
4. `## 3. File Formats & Schemas` — must contain subsections for file groups
5. `## 4. Special Notes` — data-level caveats

**How to verify**: Parse data_description.md headings and match against the numbered pattern.

**Pass criteria**: All 4 numbered sections present with correct heading format, and Section 1 contains a code block.

**Fail criteria**: Any section missing or malformed.

**Error message format**: `"data_description.md missing or malformed section: expected '## {n}. {section_name}'"`

---

## Phase 2: Information Firewall Verification

### C2.1: No Paper References in README

**What to verify**: README contains no references to the original paper.

**High-confidence patterns** (always a violation):
- DOI patterns: `10.\d{4,}/`, `doi.org/`
- "et al." (author citation pattern)
- Explicit attribution phrases: "the authors propose", "the authors show", "the paper presents", "in this paper", "the original paper"
- Bibliographic patterns: `[Author, Year]`, `(Author et al., Year)`, `arXiv:\d+`

**Context-dependent patterns** (only a violation when used in a bibliographic or attribution sense):
- Journal names: Nature, Science, Cell, PNAS, etc.
  - Violation: "published in Nature", "Nature 2023", "a Cell paper"
  - NOT a violation: "cell type", "cell line", "single-cell RNA", "nature of the problem", "natural language", "science behind"
- "this study"
  - Violation: "this study proposes", "this study demonstrates" (referring to the paper's contribution)
  - NOT a violation: "this study's dataset was collected from..." (referring to the data source in a factual, non-attributive way)
- "the paper"
  - Violation: "the paper introduces", "as described in the paper"
  - NOT a violation: rarely legitimate in benchmark docs — flag if appears

**How to verify**:
1. Search README for high-confidence patterns → immediate fail
2. Search for context-dependent patterns → check surrounding words to disambiguate:
   - Extract the sentence containing the match
   - If the match is part of a compound word or domain phrase (e.g., "cell line", "single-cell"), pass
   - If the match appears with publication verbs (propose, present, show, demonstrate, publish, report) or temporal markers (year, volume, issue), fail

**Pass criteria**: No paper references found after disambiguation.

**Fail criteria**: Any confirmed paper reference detected.

**Error message format**: `"Paper reference found in README: '{matched_text}' at line {line}"`

---

### C2.2: No Paper References in data_description.md

**What to verify**: data_description.md contains no references to the original paper.

**Patterns to detect**: Same as C2.1 (both high-confidence and context-dependent, with same disambiguation rules).

**How to verify**: Same as C2.1, applied to data_description.md.

**Pass criteria**: No paper references found after disambiguation.

**Fail criteria**: Any confirmed paper reference detected.

**Error message format**: `"Paper reference found in data_description.md: '{matched_text}' at line {line}"`

---

### C2.3: No Algorithm Names in README

**What to verify**: README contains no mentions of the algorithm name from the paper.

**How to verify**:
1. If filter_result.json exists, read `task_info.algorithm` field
2. Search README for this algorithm name (case-insensitive)

**Pass criteria**: Algorithm name not found in README.

**Fail criteria**: Algorithm name found.

**Error message format**: `"Algorithm name '{algorithm}' found in README at line {line}"`

**Note**: If filter_result.json doesn't exist, skip this check with warning.

---

### C2.4: No Algorithm Names in data_description.md

**What to verify**: data_description.md contains no mentions of the algorithm name.

**How to verify**: Same as C2.3 but for data_description.md.

**Pass criteria**: Algorithm name not found.

**Fail criteria**: Algorithm name found.

**Error message format**: `"Algorithm name '{algorithm}' found in data_description.md at line {line}"`

---

### C2.5: No Prescriptive Method Guidance in README

**What to verify**: README does not prescribe or suggest specific solution approaches, architectures, or hyperparameter choices to the solver.

**Core principle**: The firewall protects against **prescriptive guidance** (telling the solver what method to use), not against **descriptive vocabulary** (domain terms that happen to overlap with ML concepts). The test is: does this text constrain or steer the solver's methodology choice?

**Violation patterns** (prescriptive — tells the solver what to do):
- Prescriptive architecture statements: "use a ResNet", "apply a Transformer-based model", "build a 3-layer CNN"
- Specific hyperparameter values: "learning rate of 0.001", "batch size 32", "train for 100 epochs", "hidden dimension 256"
- Training procedure instructions: "use Adam optimizer", "apply cosine annealing schedule", "use dropout of 0.5"
- Solution approach directives: "fine-tune BERT", "use transfer learning from ImageNet", "apply data augmentation"

**NOT violations** (descriptive — part of the task/data/domain):
- Data-grounded model references: If a pre-trained model file exists in `problem/data/` (e.g., `pretrained_weights.pth`), referencing it in README is allowed — the model is part of the task's initial data, not a method prescription
- Domain vocabulary that overlaps with ML terms: "cell type", "attention span" (psychology), "transformer station" (power grid), "recurrent episodes" (medicine), "convolutional filter" (signal processing)
- Task-descriptive terms: "the model should output a probability distribution" (describes output format, not architecture), "predictions should generalize across domains" (describes objective, not method)
- Hyperparameter names without values as data schema terms: a CSV column named "learning_rate" in the dataset is data, not a method prescription

**How to verify**:
1. Search README for ML architecture names (ResNet, BERT, Transformer, CNN, LSTM, GRU, U-Net, GAN, VAE, GPT, etc.), hyperparameter terms (learning rate, batch size, epochs, layers, hidden units, dropout), and training terms (optimizer, schedule, fine-tune, pre-train)
2. For each match, apply these automated disambiguation rules in order:
   a. **Data-grounded exception**: Check if the term references a file that actually exists in `problem/data/`. If yes → pass
   b. **Prescriptive verb test**: Check if the term appears with prescriptive verbs/patterns: "use [term]", "apply [term]", "set [term] to [value]", "train with [term]", "[term] should be [value]". If yes → fail
   c. **Specific value test**: Check if a hyperparameter term is accompanied by a specific numeric value (e.g., "learning rate 0.001", "128 hidden units"). If yes → fail
   d. **Compound-word / domain-phrase test**: Check if the term is part of a larger domain-specific compound (e.g., "cell" in "cell line", "transformer" in "transformer station"). If the surrounding words form a recognized non-ML compound → pass
   e. **Standalone mention without prescription**: If the term appears in a descriptive/explanatory context without prescriptive verbs or specific values (e.g., "this is a sequence prediction task" mentioning "LSTM" as background context) → pass. The term alone, without a directive to use it, is not a violation

**Pass criteria**: No prescriptive method guidance found after disambiguation.

**Fail criteria**: Prescriptive guidance detected (directive to use a specific architecture, specific hyperparameter values, or training procedure instructions).

**Error message format**: `"Prescriptive method guidance found in README: '{matched_text}' at line {line}"`

**Note**: When in doubt between "prescriptive" and "descriptive", check: if you removed this sentence, would the solver lose information about **what to do** (the task) or **how to do it** (the method)? Only the latter is a violation.

---

### C2.6: No References to evaluation/ or Ground Truth Directory

**What to verify**: README and data_description.md do not reveal the evaluation system's internal structure or suggest the existence of hidden test data.

**Patterns to detect**:
- `evaluation/` (the directory path)
- `ground_truth/` (the directory path)
- "hidden test set"
- "held-out test set" (when referring to evaluator-side data)
- Phrases explicitly revealing evaluation internals

**Allowed terminology** (standard ML terms, NOT violations):
- "ground truth" (as a general term for correct labels/answers)
- "true labels", "correct answers", "reference values"
- "gold standard", "oracle"
- "target values", "actual outcomes"
- Any standard ML terminology describing what the model should predict

**How to verify**: Search both files for prohibited patterns. Ignore standard ML terminology.

**Pass criteria**: No evaluation system internals revealed.

**Fail criteria**: Evaluation directory paths or hidden data structure exposed.

**Error message format**: `"Reference to evaluation internals found in {file}: '{matched_text}' at line {line}"`

**Note**: The goal is to prevent solvers from knowing about the evaluation system's file structure, not to ban standard ML terminology.

---

## Phase 3: Benchmark Design Principles

### C3.1: All Initial Data Present

**What to verify**: problem/data/ contains all D_dev components (training data, validation data, pretrained models if applicable).

**How to verify**:
1. Read data_description.md to understand expected data structure
2. Check if training and validation data exist for each instance
3. If task mentions pretrained models, check if they exist. **Exception**: when data_description.md or filter_result.json indicates a cross-setting dependency (pretrain→finetune), the pretrained model is intentionally absent for dependent instances — the Solver obtains it by first solving the source instance. Do not flag this as missing.

**Pass criteria**: All expected D_dev components present.

**Fail criteria**: Missing training or validation data.

**Error message format**: `"Missing initial data for instance '{instance}': expected {expected_files}, found {found_files}"`

**Note**: This is a heuristic check. Look for common patterns like train.csv, train.npy, valid.csv, etc.

---

### C3.2: No Algorithm Artifacts in problem/data/ or evaluation/

**What to verify**: problem/data/ and evaluation/ contain no outputs or artifacts from algorithm A.

**Patterns to detect**:
- Experiment outputs: results/, outputs/, predictions/
- Logs: logs/, *.log
- Checkpoints: checkpoints/, *.ckpt, *.pth, *.h5 (unless explicitly pretrained models required by the task). **Note**: for cross-setting dependency instances (where the pretrained model comes from another instance's training), the pretrained model is an Algorithm A output and should NOT be present — flag it if found.
- Cache files: __pycache__/, *.pyc, .cache/

**How to verify**: Scan problem/data/ and evaluation/ for these patterns

**Pass criteria**: No algorithm artifacts found.

**Fail criteria**: Artifacts detected.

**Error message format**: `"Algorithm artifact found: {path}"`


---

### C3.3: README Has All Required Sections

**What to verify**: README contains all 6 required sections.

**Required sections**:
1. Scientific Problem
2. Task Objective
3. Dataset Information
4. Evaluation Metrics — must contain a Primary Metric subsection
5. Output Format
6. Submission Guidelines — must contain an Entry Point subsection

**How to verify**: Parse README headings and check for these sections (allow minor variations in wording).

**Pass criteria**: All 6 sections present.

**Fail criteria**: Any section missing.

**Error message format**: `"README missing required section: {section}"`

---

### C3.4: Output Format Specification Complete

**What to verify**: README Section 5 (Output Format) includes all necessary details for a solver to produce correct output.

**Required information** (presentation format is flexible):
- Filename or filename pattern
- File format (CSV, NPY, JSON, etc.)
- Shape/structure (dimensions, columns, keys) — where applicable
- Data types (int, float, string, etc.) — where applicable
- Value constraints (e.g., "probabilities in [0,1]", "valid SMILES parseable by RDKit", "integer labels in [0, k-1]"). If the output domain is unconstrained, the spec should say so explicitly (e.g., "real-valued predictions").
- Output path pattern (e.g., `output/{instance_name}/filename`)

**How to verify**: Parse Section 5 and check that these information elements are present. They may be in a table, prose, or mixed format.

**Pass criteria**: All applicable details present.

**Fail criteria**: Any critical detail missing (filename, format, or output path at minimum).

**Error message format**: `"Output format specification incomplete: missing {missing_details}"`

---

### C3.5: Submission Guidelines Include INSTANCES List

**What to verify**: README Section 6 includes populated INSTANCES list and data loading example.

**How to verify**:
1. Check if Section 6 contains INSTANCES variable
2. Check if INSTANCES is populated (not empty or placeholder)
3. Check if there's a data loading example

**Pass criteria**: INSTANCES list is populated with actual instance names.

**Fail criteria**: INSTANCES is empty, placeholder, or missing.

**Error message format**: `"Submission guidelines missing populated INSTANCES list"`

---

### C3.6: All Metrics Have SOTA Scores

**What to verify**: All metrics in README have SOTA scores (paper's proposed method) in metadata.json.

**How to verify**:
1. Extract metrics from README Section 4
2. For each metric, check if metadata.json has non-null `sota_score`

**Pass criteria**: Every metric has a non-null `sota_score`.

**Fail criteria**: Any metric has `sota_score` as null or missing.

**Error message format**: `"Metric '{metric}' lacks SOTA score in metadata.json"`

**Note**: `baseline_score` may be null if the paper doesn't report baselines — that's acceptable.

---

### C3.7: Oracle/Scorer Placement and Originality

**What to verify**: For tasks that use Oracle/scorer components (Oracle-type and Distribution-type with scorer), both the solver side and evaluator side have the Oracle components they need. Additionally, when Oracle components include re-implemented `.py` files, verify they are genuinely re-implemented rather than directly copied from the original repository.

Oracle components can take any form: scripts, data files, model weights, executables, simulators, configurations, library dependencies, etc. Pure library Oracles (e.g., RDKit QED available via Dockerfile) need no extra files on either side.

**How to verify**:

*Placement check:*
1. Detect Oracle/scorer tasks from README keywords: "optimize", "maximize", "minimize", "generate", "scorer", "oracle", "simulator", "objective function"
2. If detected, check both sides:
   - **Solver side**: if solver needs Oracle access → `problem/data/{instance}/` should contain Oracle components
   - **Evaluator side**: if evaluator needs Oracle for scoring → `evaluation/` should contain Oracle components (in `ground_truth/`, `shared/`, or inline in `evaluator.py` — any location within `evaluation/`)
3. Pure library Oracle (no extra files needed) → pass on both sides
4. Cannot determine task type → skip with warning

*Code originality check (when Oracle components include `.py` files in `evaluation/`):*
5. If `repositories/` exists, compare Oracle `.py` files against repository originals
6. Signs of direct copying (multiple indicators together suggest a copy):
   - Retains original repository copyright/license headers
   - Retains functions unrelated to evaluation (e.g., original file has 10 functions but evaluation only needs 2, yet all are kept)
   - Uses deprecated APIs or requires monkey-patches to run with current dependency versions
   - File structure and function signatures match the repository original with only minimal compatibility patches added
7. Signs of proper re-implementation: only evaluation-relevant functions retained, current API usage, code restructured, no original repository headers
8. If `repositories/` does not exist, skip originality check with a note

*Solver-side and inlined code originality:*
9. If Oracle `.py` files also exist in `problem/data/{instance}/`, apply the same originality check (steps 5-8) against repository originals.
10. If evaluator.py contains inlined metric computation functions (not just imports from a standalone script), compare against author evaluation files in `repositories/`. Same copying indicators apply.

*Script usability and cleaning check:*
11. For any `.py` scripts in `evaluation/` or `problem/data/` (Oracle scripts, benchmark evaluation scripts, simulators, auxiliary modules, etc.), verify:
    a. **No irrelevant content**: Check for signs of uncleaned code — unused functions, plotting/visualization imports (`matplotlib.pyplot`, `seaborn`) without evaluation purpose, argparse blocks, standalone `if __name__ == "__main__"` test harnesses that are not the script's intended execution mode, logging setup code.
    b. **No harmful content**: Check for Algorithm A methodology leakage — functions that implement training loops, model architecture definitions, or the paper's proposed algorithmic logic. Cross-reference against `repositories/` to identify method-specific code that should have been stripped.
    c. **Usability**: Library imports are resolvable against the task's target environment (`environment/Dockerfile.v3` + base image `.claude/skills/task-build/references/Dockerfile.base.v3`) — check not only that imports exist, but also that version-sensitive API calls are compatible with the library versions in the base image (e.g., deprecated/removed functions, renamed parameters, changed return types); file paths are relative to the task package structure (no hardcoded repository paths); no syntax errors.

**Pass criteria**: Both sides have what they need (or pure library Oracle, or not an Oracle task); and any Oracle-related code — standalone `.py` files in `evaluation/` or `problem/data/`, AND metric functions inlined in `evaluator.py` — shows signs of genuine re-implementation rather than direct copying; and all scripts pass the cleaning check.

**Fail criteria**: Oracle task but either side missing needed components; or Oracle-related code (standalone or inlined) appears to be directly copied from the original repository; or scripts contain harmful content (Algorithm A leakage).

**Warning criteria**: Scripts contain irrelevant content (dead code, plotting imports, etc.) — functional but indicates incomplete cleaning.

**Error message format**:
- `"Solver needs Oracle access, but no Oracle components found in problem/data/{instance}/."`
- `"Evaluator needs Oracle for scoring, but no Oracle components found in evaluation/ for instance '{instance}'."`
- `"File '{path}' in evaluation/ appears to be directly copied from the original repository rather than re-implemented: {evidence}. Per task-build rules, author code must be re-implemented, not copied."`
- `"File '{path}' in problem/data/ appears to be directly copied from the original repository rather than re-implemented: {evidence}."`
- `"Metric function(s) in evaluator.py appear to be copied from '{repo_file}' with only cosmetic changes: {evidence}. Author-implemented functions must be genuinely re-implemented."`
- `"Script '{path}' contains harmful content (Algorithm A leakage): {evidence}. Method-specific code must be stripped to maintain the information firewall."`
- `"Script '{path}' contains irrelevant content that should have been cleaned: {evidence} (e.g., unused functions, plotting imports, argparse blocks)."`
- `"Script '{path}' has usability issues: {evidence} (e.g., unresolved imports, hardcoded repository paths, syntax errors)."`

**Skip message**: `"Cannot determine Y_ref type from README; skipping Oracle placement check."`

---

## Phase 4: Dynamic Testing

### C4.1: Generate Baseline Solver

**What to verify**: Can generate a functional baseline solver for this task.

**How to verify**:
1. Try `scripts/generate_baseline.py` with task package path
2. If it returns code, use that
3. If it fails, manually analyze task and write baseline code

**Pass criteria**: Baseline solver code generated successfully.

**Fail criteria**: Cannot generate baseline solver (should not happen - skill must handle all cases).

**Error message format**: `"Failed to generate baseline solver: {error}"`

---

### C4.2: Run Baseline Solver

**What to verify**: Baseline solver runs without errors on all instances.

**How to verify**:
1. Write baseline solver to temporary workspace/
2. Run it: `python workspace/run.py`
3. Check exit code and stderr

**Pass criteria**: Solver completes with exit code 0.

**Fail criteria**: Solver crashes or returns non-zero exit code.

**Error message format**: `"Baseline solver failed on instance '{instance}': {error}"`

---

### C4.3: Validate Output Files

**What to verify**: Baseline solver produces output files matching README specification.

**How to verify**:
1. Check if output files exist at expected paths
2. Check if file format matches (CSV, NPY, etc.)
3. Check if shape/structure matches

**Pass criteria**: All output files exist and match specification.

**Fail criteria**: Missing files or format mismatch.

**Error message format**: `"Output file mismatch for instance '{instance}': expected {expected}, found {found}"`

---

### C4.4: Run Evaluator

**What to verify**: evaluator.py runs without errors on baseline outputs.

**How to verify**:
1. Set OUTPUT_DIR environment variable to baseline output directory
2. Run: `python evaluation/evaluator.py`
3. Check exit code and stderr

**Pass criteria**: Evaluator completes with exit code 0.

**Fail criteria**: Evaluator crashes or returns non-zero exit code.

**Error message format**: `"Evaluator failed: {error}"`

---

### C4.5: Verify Evaluator Output Structure

**What to verify**: Evaluator produces score.json with correct structure.

**How to verify**:
1. Check if score.json exists
2. Parse as JSON
3. Check if it contains all instances and all metrics

**Pass criteria**: score.json has correct structure.

**Fail criteria**: Missing score.json, invalid JSON, or incomplete structure.

**Error message format**: `"Evaluator output structure incorrect: {issue}"`

---

### C4.6: Sanity Check Scores

**What to verify**: Baseline scores are within valid range and not suspiciously perfect/broken.

**How to verify**:
1. For each metric, check if score is within valid range (e.g., 0-1 for accuracy, 0-100 for percentage)
2. Check if scores are not suspiciously perfect (e.g., 100% accuracy on random baseline)
3. Check if scores are not broken (e.g., NaN, Inf, negative when should be positive)

**Pass criteria**: All scores are reasonable.

**Fail criteria**: Any score is invalid or suspicious.

**Error message format**: `"Suspicious baseline score for '{metric}' on instance '{instance}': {score} (expected range: {range})"`

**Note**: This is a warning, not a hard failure.

---

### C4.7: Verify Interface Conformance

**What to verify**: Generated baseline solver conforms to README Section 6 interface specification.

**How to verify**:
1. Check if workspace/run.py exists
2. Check if `main()` function is defined
3. Check if `INSTANCES` list is defined and matches actual instances
4. Check if `DATA_DIR` and `OUTPUT_DIR` are defined
5. Verify `if __name__ == "__main__": main()` pattern exists

**Pass criteria**: Baseline solver conforms to interface.

**Fail criteria**: Interface mismatch (missing main(), INSTANCES, or environment variables).

**Error message format**: `"Baseline solver interface mismatch: {issue}"`

**Note**: This is a secondary check to confirm C1.6 from a different angle. The interface uses a simple `main()` function pattern, not a Solution class.

---

### C4.8: Evaluator Correctness — Ground Truth Test

**What to verify**: Evaluator produces near-perfect scores when given ground truth as solver output. This catches evaluator bugs such as wrong formula, flipped metric direction, off-by-one errors, or incorrect normalization.

**How to verify**:

Step 1 — Understand format mapping:
1. Read evaluator.py's `load_ground_truth()` (or equivalent) to understand how ground truth is loaded (format, columns, shape)
2. Read evaluator.py's `load_and_validate()` to understand expected solver output format (filename, columns, dtype, shape)
3. Read `calculate_metrics()` to understand what the evaluator computes and how
4. Determine the mapping: what solver output, if it represented perfect predictions, would produce optimal scores?

Step 2 — Construct perfect prediction:
Based on the format mapping from Step 1, write a Python script that:
1. Reads ground truth from evaluation/ground_truth/{instance}/
2. Transforms it into the expected solver output format:
   - Classification with label output: copy labels directly
   - Classification with probability output: set P=1.0 for true class, 0.0 for others
   - Regression: copy target values directly
   - Ranking: produce perfect ranking order
   - Generation: if ground truth is a reference set, use the references themselves
   - Custom format: infer from calculate_metrics() what input would maximize/minimize each metric
3. Saves to temporary output directory with correct filename and structure per README Section 5

Step 3 — Run evaluator and verify:
1. Run evaluator on the perfect-prediction output using scripts/run_baseline_test.py
2. Check each metric against expected perfect values:
   - Accuracy, F1, AUC, Precision, Recall → expect ≥0.99
   - Error metrics (RMSE, MAE, MSE) → expect ≤1e-6
   - Correlation (Pearson, Spearman) → expect ≥0.99
   - Metrics without a clear perfect value (FCD, perplexity) → verify score is substantially better than baseline score from C4.6
3. If any metric is far from perfect, report as failure with the actual score and expected range

**Pass criteria**: All metrics show near-perfect scores consistent with receiving ground truth as input.

**Fail criteria**: Any metric shows a score clearly wrong for a perfect prediction (e.g., accuracy of 0.5 when given ground truth labels, or RMSE > 0.01 when predictions equal targets).

**Error message format**: `"Evaluator correctness issue: metric '{metric}' scored {score} on ground truth input (expected {expected_range}). This suggests a bug in the evaluator's scoring logic."`

**Skip criteria**: Oracle-type tasks where ground truth is not a static file (evaluator wraps an oracle/scorer function) → skip with note: `"Skipped C4.8: Oracle-type task — no static ground truth for correctness test."`

---

### C4.9: Evaluator Robustness — Malformed Input Test

**What to verify**: Evaluator handles invalid solver outputs gracefully — returns error results with null metrics instead of crashing or producing silent garbage scores.

**How to verify**: For ONE representative instance, test these 6 malformed inputs:

1. **Missing file**: Delete the expected output file entirely
2. **Empty file**: Create a 0-byte file at the expected output path
3. **Wrong format**: If output should be CSV, provide a plain text file with random content (and vice versa)
4. **Invalid values**: Create a correctly-formatted output file but fill numeric fields with NaN or Inf
5. **Wrong sample count**: Create a correctly-formatted output file but with fewer or more rows/samples than expected (e.g., half the expected count)
6. **Misaligned IDs**: If output contains sample/row identifiers, create a file with valid format and count but with IDs that don't match ground truth (shuffled, duplicated, or non-existent IDs)

For each test:
1. Set up the malformed output in a temporary directory
2. Run evaluator
3. Check result — evaluator should either:
   - Return error_result with null metrics and an error message (PREFERRED)
   - Exit with non-zero code and clear error on stderr (ACCEPTABLE)
   - NOT: return numeric scores as if nothing is wrong (FAIL)
   - NOT: crash with unhandled exception / traceback without producing any result (WARNING)

**Pass criteria**: Evaluator handles all 6 malformed cases without producing false scores.

**Fail criteria**: Evaluator produces numeric scores (not null, not NaN) for any malformed input — this means it silently ignores invalid data.

**Warning criteria**: Evaluator crashes with unhandled exception instead of returning error_result. Functional but not robust.

**Error message format**: `"Evaluator robustness issue: produced scores {scores} when given {test_case} for instance '{instance}'. Expected null metrics or error exit."`

**Note**: This test uses only ONE instance to minimize runtime. If the output format does not use sample IDs, skip test 6. The goal is to verify the evaluator's validation logic exists, not exhaustive fuzzing.
