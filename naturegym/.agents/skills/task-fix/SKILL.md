---
name: task-fix
description: Fix issues identified by task-verify in a task package. Reads task_verify_result.json, prioritizes failed checks over warnings, applies targeted fixes following task-build rules, re-runs dynamic testing, and outputs a fix log.
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash, WebFetch, Write, Edit
---

# Task-Fix Skill

Fix issues in a task package identified by task-verify, following task-build rules and conventions.

## Input Requirements

Before invoking this skill, provide:
1. **Task Package Path**: Directory containing the task package (`problem/`, `evaluation/`, `environment/`, `metadata.json`)
2. **Paper Folder Path**: Directory containing the original paper and prior processing results (needed for context)

The task package directory must contain:
- `task_verify_result.json`: Output from task-verify (the issues to fix)

The paper folder must contain:
- `{paper_id}.pdf` and `{paper_id}.html`: Original paper files
- `preprocessed/`: paper-preprocess output (`text.md`, `links.json`, `figures/`, `tables/`)
- `filter_result.json`: Combined output from paper-filter + data-check
- `repositories/`: Cloned repositories (reference only)

**NOTE**: The task package path and paper folder path may be the same directory (task-build often builds in-place).

## Output

**CRITICAL**: This skill MUST output both items below, even if no fixes were applied:

1. **Fixed task package**: Modified files in the task package directory
2. **Fix log**: `task_fix_log.txt` written to the task package directory

## Core Principles

### 1. Targeted Fixes, Not Rebuilds

This skill makes **targeted, minimal fixes** to resolve specific verification failures. It does NOT rebuild the task package from scratch — that is task-build's job. Each fix should change only what is necessary to resolve the identified issue.

### 2. Priority Order

Process issues in this order:
1. **Failed checks** — must be resolved (these cause `overall_status: "failed"`)
2. **Warnings** — should be resolved where possible (non-critical but improve quality)

### 3. Fix Dependency Order

Within each priority level, fix in phase order since later fixes may depend on earlier ones:
- Phase 0 (file structure) → Phase 1 (consistency) → Phase 2 (information firewall) → Phase 3 (benchmark design) → Phase 4 (dynamic testing)

### 4. Source of Truth Hierarchy

When fixing cross-file consistency issues (C1.x), follow this hierarchy to determine the canonical value:

| Element | Source of Truth | Rationale |
|---------|----------------|-----------|
| Instance names | `problem/data/` directories | Physical data is ground truth |
| Metric names | Paper → `filter_result.json` → README | Determined by paper's evaluation methodology |
| Metric direction | Paper → `filter_result.json` | Paper defines what higher/lower means |
| Task name | README heading | README is the user-facing document |
| Output format | README Section 5 | README is the specification |
| Ground truth paths | `evaluation/ground_truth/` actual files | Physical files are ground truth |

When the source of truth itself appears wrong (e.g., instance directories don't match filter_result.json), consult the paper and filter_result.json to determine the correct state, then fix the source of truth first.

### 5. task-build Rule Compliance

All fixes must comply with task-build rules. Key rules to observe:
- **Information Firewall**: No paper references, algorithm names, method details, or evaluation internals in solver-visible files (`problem/`)
- **Metric Consistency**: Metric names must be identical (case-sensitive) across README, evaluator.py, and metadata.json
- **Output Format**: README Section 5, evaluator.py validation, and evaluator.py scoring must all agree
- **Evaluator Structure**: Follow the evaluator template pattern from task-build's evaluator_guide

### 6. Evidence-Based Fixes

Every fix must be traceable to:
- The specific check_id from task_verify_result.json
- The task-build rule or convention being followed
- The evidence source (paper, filter_result.json, physical files)

Never guess or fabricate — if a fix requires information not available, flag it for manual review.

## Workflow

### Phase 0: Assess

1. Read `task_verify_result.json` from the task package directory
2. If `overall_status` is `"pass"` and no warnings exist, output an empty fix log and stop
3. Read all task package files to understand current state:
   - `problem/README.md`
   - `problem/data_description.md`
   - `evaluation/evaluator.py`
   - `metadata.json`
   - `environment/Dockerfile.v3` (if exists)
4. Read paper context:
   - `filter_result.json` — primary structured context
   - `preprocessed/text.md` — paper content for domain understanding
5. Categorize all issues into: failed_checks (priority) and warnings (secondary)
6. Order issues by phase (C0 → C1 → C2 → C3 → C4) within each priority level
7. Identify cross-dependencies between issues (e.g., fixing C1.3 metric names may also resolve C4.5 evaluator output structure)

### Phase 1: Fix Failed Checks

Read [references/fix_rules.md](references/fix_rules.md) for detailed fix strategies per check.

Process each failed check in phase order. For each fix:
1. Read the `issue` and `location` fields to understand the specific problem
2. Read the affected file(s) at the indicated locations
3. Determine the correct fix following the source of truth hierarchy and task-build rules
4. Apply the fix using Edit (preferred) or Write (for regeneration)
5. Verify the fix is consistent with other files (check for cascading inconsistencies)

**Cross-dependency handling**: After fixing a check, scan remaining issues to see if any are now resolved as a side effect. Mark these as resolved in the fix log.

### Phase 2: Fix Warnings

Same approach as Phase 1, but for warning-level issues. Some warnings may already be resolved as side effects of fail fixes.

### Phase 3: Post-Fix Consistency Verification

After all fixes are applied, perform a lightweight consistency scan:

1. **Metric name alignment**: Extract metric names from README, evaluator.py, and metadata.json — confirm they match
2. **Instance name alignment**: Extract instance names from README Section 6, evaluator.py INSTANCES, data_description.md, metadata.json, and filesystem — confirm they match
3. **Output format alignment**: Confirm README Section 5 output specification matches evaluator.py loading logic
4. **Ground truth paths**: Confirm evaluator.py references existing files in evaluation/ground_truth/
5. **Information firewall**: Quick scan of README and data_description.md for paper references, algorithm names

If any new inconsistencies are found, fix them and log the additional fixes.

### Phase 4: Dynamic Re-Testing

If any Phase 4 (C4.x) checks were in the original failed_checks OR if fixes to evaluator.py/README output format were made:

1. Copy the `scripts/run_baseline_test.py` from the task-verify skill directory
2. Generate a baseline solver following the same strategy as task-verify:
   - Copy run.py template from README Section 6
   - Read README Section 5 + data_description.md for output format and data format
   - Fill in data loading and minimal baseline prediction logic
3. Run `python scripts/run_baseline_test.py <task_package_path> <workspace_path>`
4. If the test passes, record baseline scores in the fix log
5. If the test fails, diagnose the issue:
   - If evaluator.py error → fix evaluator.py and re-test
   - If output format mismatch → align README/evaluator and re-test
   - If data loading error → check data paths and fix baseline
   - Maximum 3 retry cycles; if still failing, flag for manual review
6. If C4.8 (evaluator correctness) was in the original failed/warning checks OR evaluator.py scoring logic was modified:
   - Re-run the ground truth test: construct perfect prediction from ground truth (see task-verify C4.8 rules), run evaluator, verify near-perfect scores
   - If scores are still wrong after fix, re-examine calculate_metrics() and retry (max 3 cycles)
7. If C4.9 (evaluator robustness) was in the original failed/warning checks OR evaluator.py validation logic was modified:
   - Re-run the robustness test: test all 6 malformed input cases on one instance
   - All cases must produce error_result or clean exit, not false scores

### Phase 5: Output Fix Log

Write `task_fix_log.txt` to the task package directory:

```text
Source: task_verify_result.json
Applied: {ISO 8601 timestamp}
Summary: {total} issues ({resolved} resolved, {partial} partial, {manual_review} manual review, {skipped} skipped)

=== FAILED CHECKS ===

[C1.3] RESOLVED
  Issue: Metric names inconsistent: README has ['RMSE', 'MAE'], evaluator.py has ['rmse', 'mae']
  Action: Aligned metric names to paper convention 'RMSE', 'MAE' in evaluator.py and metadata.json
  Files: problem/README.md:45, evaluation/evaluator.py:12, metadata.json
  Side effect: Also resolved C4.5 (score.json structure now correct)

[C2.1] RESOLVED
  Issue: Paper reference found in README: 'Nature Machine Intelligence' at line 8
  Action: Replaced journal name with neutral domain language
  Files: problem/README.md:8

[C3.1] MANUAL REVIEW NEEDED
  Issue: Missing training data for instance 'dataset_a'
  Reason: Cannot auto-generate training data — requires human acquisition from original source

=== WARNINGS ===

[C3.7] RESOLVED
  Issue: Metric 'R2' in README lacks baseline score in metadata.json
  Action: Extracted score from paper Table 3: R2 = 0.89 (LinearRegression baseline)
  Files: metadata.json

[C0.5] RESOLVED
  Issue: Dockerfile missing FROM instruction
  Action: Added FROM naturebench-base:v3 as first line
  Files: environment/Dockerfile.v3

=== DYNAMIC RETEST ===

Status: pass
Baseline scores:
  instance_1: {RMSE: 1.234, MAE: 0.987}
  instance_2: {RMSE: 2.345, MAE: 1.876}
Ground truth scores:
  instance_1: {RMSE: 0.0, MAE: 0.0}
  instance_2: {RMSE: 0.0, MAE: 0.0}
Robustness test (instance_1):
  missing_file: error_result
  empty_file: error_result
  wrong_format: error_result
  invalid_values: error_result
  wrong_sample_count: error_result
  misaligned_ids: skipped (no sample IDs in output format)
```

**Resolution tags**:
- `RESOLVED` — issue fully fixed
- `PARTIAL` — partially addressed but may need further attention
- `MANUAL REVIEW NEEDED` — cannot be fixed automatically, requires human intervention
- `SKIPPED` — warning-level issue intentionally not addressed (with reason)

## Escalation: Issues That Cannot Be Auto-Fixed

Some issues require human intervention. Flag these in `manual_review_needed` and continue fixing other issues:

- **C0.1 missing files** that require regeneration from scratch (e.g., entire evaluator.py missing)
- **C3.1 missing data** that requires re-acquisition or data processing
- **C1.7 missing ground truth** that cannot be extracted from existing data
- **C3.7 Oracle re-implementation** that requires deep domain understanding
- **C4.8 evaluator correctness** where metric formula involves domain-specific math that cannot be verified from the paper alone
- **C4.x persistent failures** after 3 retry cycles

Do NOT stop the fix process because of unfixable issues — fix everything that can be fixed and flag the rest.
