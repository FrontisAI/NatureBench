---
name: task-verify
description: Verify task packages built by task-build. Checks document consistency, benchmark design principles, and performs dynamic testing with a baseline solver to ensure the task package is valid and usable.
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Write, Bash(python *), Bash(find *), Bash(ls *), Bash(mkdir *), Bash(rm *), Bash(cp *)
---

# Task-Verify Skill

Verify that a task package built by task-build is valid, consistent, and usable as a benchmark.

## Input Requirements

User provides:
- **task_package_path**: Path to task package directory containing problem/, evaluation/, metadata.json

Optional:
- **filter_result.json**: If present in task package, used for algorithm name verification (C2.3, C2.4)

## Verification Workflow

Execute 5 phases with 36 checks total. If Phase 0 fails, terminate immediately. The check count MUST be exactly 36. Do not skip, merge, or invent checks beyond this list.

### Phase 0: File Completeness & Structure (5 checks)

Fast-fail validation. See [references/verification_rules.md](references/verification_rules.md) for detailed rules.

- C0.1: Required files exist
- C0.2: Instance directories match between problem/data/ and evaluation/ground_truth/
- C0.3: metadata.json is valid JSON with required fields
- C0.4: evaluator.py has valid Python syntax
- C0.5: Dockerfile.v3 dependency viability (compatibility, availability, API compatibility)

### Phase 1: Cross-File Consistency (9 checks)

Ensure all documents agree on key information. See [references/verification_rules.md](references/verification_rules.md).

- C1.1: Task name matches between README and metadata.json
- C1.2: Instance names consistent across all files and directories
- C1.3: Metric names consistent across README, metadata, evaluator
- C1.4: Metric directions match between README and metadata
- C1.5: Exactly one primary metric designated in README
- C1.6: Output format in README matches evaluator expectations
- C1.7: Ground truth paths in evaluator actually exist
- C1.8: data_description.md directory structure matches actual files in problem/data/
- C1.9: data_description.md has required section structure (Directory Structure, Dataset Overview, File Formats & Schemas, Special Notes)

### Phase 2: Information Firewall Verification (6 checks)

Prevent paper/algorithm information leakage. See [references/verification_rules.md](references/verification_rules.md).

- C2.1: No paper references in README
- C2.2: No paper references in data_description.md
- C2.3: No algorithm names in README
- C2.4: No algorithm names in data_description.md
- C2.5: No prescriptive method guidance in README
- C2.6: No references to evaluation directory structure or hidden test data in solver-facing documents

### Phase 3: Benchmark Design Principles (7 checks)

Validate fairness, testability, and clarity. See [references/verification_rules.md](references/verification_rules.md).

- C3.1: All initial data present in problem/data/
- C3.2: No algorithm artifacts in problem/data/
- C3.3: README has all required sections
- C3.4: Output format specification complete
- C3.5: Submission guidelines include populated INSTANCES list
- C3.6: All metrics have SOTA scores in metadata
- C3.7: Oracle/scorer placement correctness and code originality

### Phase 4: Dynamic Testing (9 checks)

End-to-end pipeline verification by running a baseline solver. See [references/baseline_solver_guide.md](references/baseline_solver_guide.md).

- C4.1: Generate task-appropriate baseline solver
- C4.2: Run baseline solver on all instances
- C4.3: Validate output files match README specification
- C4.4: Run evaluator.py on baseline outputs
- C4.5: Verify evaluator produces correct structure
- C4.6: Sanity check scores
- C4.7: Verify baseline solver conforms to README interface
- C4.8: Evaluator correctness test (ground truth as perfect prediction)
- C4.9: Evaluator robustness test (6 malformed input cases)

**Dynamic Testing Strategy**:
1. Copy run.py template from README Section 6
2. Read README Section 5 + data_description to understand output format and data format
3. Fill in data loading and baseline prediction logic
4. Use `scripts/run_baseline_test.py` to run solver + evaluator and get actual scores
5. Must achieve 100% coverage - no skipping dynamic tests

## Output

Writes `task_verify_result.json` to the task package directory.

Schema: see [references/output_schema.md](references/output_schema.md)

Key principles:
- Only report failures and warnings (passed checks omitted for brevity)
- Each issue includes specific file paths and line numbers
- Dynamic test results include baseline scores for reference

## Critical Rules

1. **Phase 0 failure → terminate immediately**: No point checking consistency if files are missing
2. **All other phases execute even if previous phases fail**: Collect all issues in one pass
3. **Dynamic testing runs in isolated temporary directory**: Prevents contamination of task package
4. **100% dynamic test coverage required**: Must handle all task types, even complex domain-specific ones
5. **All file paths in output are absolute**: For traceability
6. **Cleanup after verification**: Remove temporary workspace/ and output/ directories after verification completes

## Execution Notes

- Read all reference files at the start to understand detailed verification rules
- For each check, provide actionable error messages with specific locations
- Dynamic testing is the most complex phase - may require custom baseline generation for unusual tasks
- Baseline solvers should be simple but functional (random/mean predictions acceptable)
