---
name: data-check
description: Acquire and verify data for CNS papers that passed paper-filter. Clones repositories, downloads and organizes datasets per evaluation setting, performs Level 4 deep verification (acquisition integrity, initial state, separability, consistency, per-setting completeness), creates an organized data environment. Updates filter_result.json with verification results, acquisition details, and task_info corrections.
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash, WebFetch, Write, Edit
---

# Data-Check Skill

Downloads repositories and datasets referenced by papers that passed paper-filter, then performs Level 4 deep verification — checking acquisition integrity, initial state, separability, consistency, per-setting completeness. Results are written back into `filter_result.json`, providing a verified data foundation for downstream task package construction.

## Context

paper-filter's Level 3 (Data Completeness) is **lightweight** — it checks link accessibility, views directory structures, and reads READMEs, but does **not actually download data**. This skill performs the actual download and deep verification, then writes results back into `filter_result.json` as **Level 4**.

### Terminology Reference

This skill uses the same core definitions as paper-filter. See [references/core_definitions.md](references/core_definitions.md) for formal definitions of:
- **T = (A, Data, M, S, B)**: The ML task tuple
- **D_dev**: Development data space (all prior information available to the original authors for solving the problem)
- **D_eval = (X_test, Y_ref)**: Evaluation data space with formal input/reference decomposition
- **Process Completeness**: The three conditions (Initial State, Evaluation Loop, Evaluation Alignment) verified per evaluation setting

## Input Requirements

Before invoking this skill, provide:
1. **Paper Folder Path**: Directory containing paper files and filter results
2. **Output Directory**: Directory for downloaded repositories and organized data

Paper folder must contain:
- `{paper_id}.pdf`: Original paper PDF
- `{paper_id}.html`: HTML version of the paper
- `filter_result.json` (paper-filter output, must have `final_result.passed == true`)
- `preprocessed/` directory (paper-preprocess output: `text.md`, `links.json`, `figures/`, `tables/`)

The original PDF and HTML serve as **additional reference** when preprocessed data does not contain sufficient detail.

## Output

This skill **updates** the existing `filter_result.json` (in the Paper Folder) by:

1. Adding `data_check_timestamp`
2. Adding `repositories[]` (clone status of all repositories)
3. Appending Level 4 to `filtering_process[]` (deep verification results, Check 4.1–4.5)
4. **Updating `task_info.data`**: adding `verification` blocks to passing `evaluation_settings[]`; moving failed settings to `rejected_settings[]`; moving recovered settings back to `evaluation_settings[]` with full `verification` blocks; and adding `recheck` explanations to unchanged `rejected_settings[]`
5. Correcting task_info errors in place with concrete evidence
6. Updating `final_result` with data-check outcome

All task_info corrections applied to `filter_result.json` are also logged to `data_check_corrections.txt` in the Paper Folder for human review.

It also creates the data environment:
```
{output_dir}/
├── repositories/                    # All cloned repositories
│   ├── {repo_name_1}/
│   └── {repo_name_2}/
└── data/                            # Acquired data, organized per setting
    ├── {setting_dir_name_1}/        # Per evaluation-setting data (original form)
    │   └── ...                      # Downloaded data files as-is
    └── {setting_dir_name_2}/
```

Data is downloaded and organized per setting but **not split**. Separability (d_dev/d_eval, d_eval→X_test/Y_ref) is difficulty-assessed and documented with structured split instructions for downstream use — actual splitting is deferred to task package construction.

**Setting directory naming**: Sanitize the setting name to a filesystem-safe identifier. See [references/acquisition_guide.md](references/acquisition_guide.md) §5 for the complete rule.

## Workflow

### Phase 1: Parse Input & Understand Context

1. Read `filter_result.json` and verify `final_result.passed == true`
2. **Comprehensively read all Level 3 results** in `filtering_process[2]`:
   - Rule 3.1: All `links_checked[]` with their status, HTTP codes, final URLs
   - Rule 3.2: `dependencies_status` (training data, validation data, pretrained model, etc.)
   - Rule 3.3: Evaluation loop assessment (reason/evidence)
   - Rule 3.4: Data consistency assessment (reason/evidence)
   - Rule 3.5: Per-setting completeness assessments
3. Extract from `task_info.data.evaluation_settings[]`:
   - Each setting's `d_dev` and `d_eval` with their `source` and `acquisition_scenario`
4. Extract from `task_info.data.rejected_settings[]`:
   - Settings that failed Level 3 and their `failure_reason` — these need re-examination
5. Extract `task_info.dependencies` for dependency checks
6. Extract `size_tier` from `filter_result.json` → `task_info.data.size_tier` (values: `"S"`, `"M"`, `"L"`, or `null` for legacy)
7. Read `preprocessed/links.json` for all repository links
8. Read `preprocessed/text.md` for paper context
9. Build the acquisition plan:
   - Repositories to clone (deduped)
   - Data to acquire per setting (both passed and rejected settings)

### Phase 2: Repository Acquisition

Clone all code/data repositories into `{output_dir}/repositories/`.

1. **Idempotency check**: If `{output_dir}/repositories/<owner>_<repo_name>/.git/` exists and `git -C <path> rev-parse HEAD` returns a valid hash, skip cloning. If `.git/` exists but HEAD is invalid, delete the directory and re-clone (git clone is not resumable).
2. Use shallow clone: `GIT_SSL_NO_VERIFY=1 git clone --depth 1 <url>` (run in foreground with `timeout: 86400000`)
3. Handle multiple repositories (e.g., code repo vs data repo separation)
4. Deduplicate: if the same content exists across multiple sources, keep the more complete version
5. Verify clone success (check `.git/` directory exists)
6. Record each repository's status and HEAD commit hash

See [references/acquisition_guide.md](references/acquisition_guide.md) §1 for detailed clone specifications.

### Phase 3: Data Acquisition

**Execution rules (apply to all sub-phases below):**
- Run all download/script Bash calls in the **foreground** — never use `run_in_background: true`.
- Set `timeout: 86400000` (24 hours) on every download, clone, and acquisition Bash call. Without an explicit timeout the Bash tool defaults to 2 minutes and will silently kill long downloads.
- Acquisition is **idempotent**: before downloading/copying/generating, check whether the target already exists. Use `wget -c` to resume partial downloads. If a session ends mid-download (e.g., a multi-day dataset exceeds 24h), the next invocation of data-check resumes from where it left off — no extra state file is needed; the filesystem itself is the progress indicator.

#### 3a: Acquire Data for Passed Settings

Sort settings by **core-priority download order** (P1 core settings first, P2 secondary settings second — see [references/acquisition_guide.md](references/acquisition_guide.md) §2 Core-Priority Download Order).

Apply the **tier-conditional download strategy** based on `size_tier` (see [references/acquisition_guide.md](references/acquisition_guide.md) §2 Download Mandate). For Tier M, monitor cumulative download size and stop remaining settings if the 100 GB limit is exceeded.

Use **shared data download deduplication** when multiple settings share the same data source URL — download once, then copy locally for subsequent settings (see [references/acquisition_guide.md](references/acquisition_guide.md) §2 Shared Data Download Deduplication).

For each `evaluation_settings[]` entry's `d_dev` and `d_eval`, acquire data based on `acquisition_scenario`:

| Scenario | Action |
|----------|--------|
| `in_repo` | Copy data from cloned repository to `data/{setting_dir}/` |
| `download_script` | Run download script from cloned repo, output to `data/{setting_dir}/` |
| `external_link` | Download from URL to `data/{setting_dir}/` |
| `generated` | Run generation script, output to `data/{setting_dir}/` |
| `restructured` | Acquire raw data + run restructuring/preprocessing script |

#### 3b: Re-examine Rejected Settings

With repositories now cloned locally, re-examine each `rejected_settings[]` entry to check whether the rejection reason still holds. Recoverable settings are promoted to `evaluation_settings[]` and removed from `rejected_settings[]`; others remain rejected with updated notes.

#### 3c: Supplementary Materials

When the paper's main text and preprocessed data do not provide sufficient detail for verification (e.g., missing performance scores, dataset version, split configuration, detailed experimental setup), download supplementary PDFs/files to obtain this information.

#### 3d: Reconcile Incremental Discoveries

If during acquisition a **new required component** or a **changed acquisition route** is discovered:
1. Update `task_info.data` and the acquisition plan with evidence.
2. Acquire the newly identified data.
3. Include it in Check 4.1–4.4 verification.

If newly required data cannot be acquired, that setting is data-incomplete and must fail Check 4.5.

See [references/acquisition_guide.md](references/acquisition_guide.md) §2–§4 for download specifications.

### Phase 4: Algorithm A Boundary Analysis & Data Component Verification

After data acquisition and before deep verification, use the cloned repository's code, the paper, and actual downloaded data files to establish the boundary between initial state and algorithm operations, verify and refine `task_info`'s data component descriptions.

#### Principles

**Provide Algorithm A with the same initial conditions it had, but do not include any of A's own operations or outputs.** The benchmark gives the Solver the same starting point as the paper's authors, then scores its output against ground truth.

#### Procedure

1. **Code & Paper Analysis**: Locate data-loading code and analyze the processing pipeline. Triangulate from paper, code, and actual data files (paper takes precedence when they conflict).
2. **Data Component Classification**: Classify each data-related file into six categories (`initial_state`, `data_preparation`, `algorithm_preprocessing_output`, `algorithm_output`, `external_resource`, `irrelevant`) and determine keep/cleanup disposition.
3. **Evaluation Mechanism Feasibility**: Identify what the evaluation mechanism requires (scorer, oracle, simulator). Flag settings where evaluation depends on Algorithm A's own components, unavailable external services, or non-existent/non-executable binaries/simulator.
4. **Reconcile with task_info**: Match classification results against `d_dev`/`d_eval` in each setting; correct missing components, mismatches, and wrongly included Algorithm A outputs.

See [references/check_rules.md](references/check_rules.md) §Data Component Classification for the complete classification table, distinction criteria, and evaluation mechanism feasibility rules.

Classification results guide Phase 6 Cleanup and inform Phase 5 verification.

### Phase 5: Deep Verification (Level 4)

Execute Check 4.1–4.5 on downloaded data. Use `scripts/inspect_data.py` for format detection and metadata extraction.

Read [references/check_rules.md](references/check_rules.md) for complete rule definitions:

- **Check 4.1**: Data Acquisition Verification — files downloaded, non-trivial size, and readable
- **Check 4.2**: Initial State Integrity — D_dev components present and accessible
- **Check 4.3**: Data Separability Verification — verify d_dev/d_eval can be separated; verify d_eval X_test/Y_ref can be separated; assess difficulty level for each dimension and overall. All verification only, no actual splitting.
- **Check 4.4**: Data Consistency — actual sample counts vs paper-reported sizes, correct version, correct dataset (the one whose scores are reported)
- **Check 4.5**: Evaluation Setting Validity & Experiment Closure — evaluation setting structural checks (merge/split/remove/scope/eval method/missing/alignment), task unity, and per-setting completeness summary

During verification, if errors are found in `task_info`:
- **Correct cautiously**: only modify fields where you have concrete evidence of error (e.g., actual data shape contradicts recorded size, metric score_source is missing a table that clearly reports scores)
- **Never change correct information**: do not modify fields that are already accurate
- **Document all corrections**: record what was changed and why in the Level 4 output

### Phase 6: Cleanup

For each setting that **passes** all Level 4 checks:

1. Apply cleanup based on Phase 4 classification results:
   - **Keep**: `initial_state`, `data_preparation`, `external_resource`
   - **Delete**: `algorithm_preprocessing_output`, `algorithm_output`, `irrelevant`
   - The data directory must ONLY contain legitimate D_dev and D_eval components
2. Ensure all nested archives have been recursively decompressed and the original archive files deleted.
3. Preserve original directory structure and file organization — do NOT split or reorganize the fundamental data files.

See [references/acquisition_guide.md](references/acquisition_guide.md) §6 for detailed cleanup rules.

### Phase 7: Write Output

1. **Update `filter_result.json`** atomically: add `data_check_timestamp`, add `repositories[]`, append Level 4 to `filtering_process[]`, add `verification` blocks to `evaluation_settings[]`, update setting status (move between `evaluation_settings[]` and `rejected_settings[]` as needed), apply task_info corrections in place, update `final_result` with data-check fields. Read [references/output_schema.md](references/output_schema.md) for the complete schema.

2. **Write `data_check_corrections.txt`** to the Paper Folder: log all task_info corrections applied across all phases for human review.

## Judgment Principles

1. **Binary per-check**: Each Check 4.x passes or fails
2. **Level 4 passes if**: Check 4.5 confirms at least one complete evaluation setting
3. **Evidence required**: Every check must cite actual file paths, sizes, shapes, or error messages
4. **No fabrication**: If a file cannot be inspected (unsupported format), report `"not_checked"` rather than guessing
5. **Cautious corrections**: Only correct task_info when concrete evidence of error exists. Document all changes.
6. **task_info as primary reference**: Use the existing task_info as the starting point for all verification. Cross-reference with the paper when discrepancies arise.
7. **Objectivity**: Report verification results as-is. If all settings fail, Level 4 fails — do not manufacture a pass. Do not interpret ambiguous evidence favorably. Do not lower verification standards for borderline cases. Failure is a valid and expected outcome.
8. **Facts over inference**: In evidence strings, clearly separate what was directly observed (file sizes, shapes, keys) from what was inferred.

## Using inspect_data.py

The script at `scripts/inspect_data.py` inspects data files for format, readability, and metadata. Three commands are available:

- `inspect <file_path>` — inspect a single file (format, readability, metadata)
- `inspect-dir <directory_path>` — inspect all data files in a directory (recursive by default)
- `verify-archive <archive_path>` — verify archive integrity

See [references/inspect_data.md](references/inspect_data.md) for output JSON structures, supported formats, and behavioral details.
