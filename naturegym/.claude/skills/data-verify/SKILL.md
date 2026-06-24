---
name: data-verify
description: Verify data components in filter_result.json after data-check. Checks Algorithm A boundary, evaluation setting validity, separability correctness, data directory integrity, and description consistency. Outputs a verification report for human review — does not modify filter_result.json or data directories.
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash(python *), Bash(python3 *), Bash(find *), Bash(wc *), Bash(head *), Bash(diff *), Write
---

# Data-Verify Skill

Verify data components produced by paper-filter and data-check. Outputs a verification report (`data_verify_result.json`) for human review — does **not** modify `filter_result.json` or data directories.

## Context

paper-filter (Level 1-3) and data-check (Level 4) run automatically and may produce systematic errors in data component classification, evaluation setting identification, and separability descriptions. This skill performs independent verification and outputs an actionable report.

### Core Principle

**Provide Algorithm A with the same initial conditions it had, but do not include any of A's own operations or outputs.**

Why: The goal is not to reproduce the paper's algorithm — it is to test whether a Solver can independently solve the same ML problem using any method, potentially surpassing the original. The benchmark gives the Solver the same starting point as the paper's authors, then scores its output against ground truth using the paper's metrics, with the paper's reported scores as baselines for comparison. Including A's outputs would leak solutions; excluding legitimate initial data would make the task unfairly harder.

### Data Component Classification

See the classification table in [references/check_rules.md](references/check_rules.md) § Terminology Reference for the six categories (`initial_state`, `data_preparation`, `algorithm_preprocessing_output`, `algorithm_output`, `external_resource`, `irrelevant`) and their definitions.

## Input Requirements

Before invoking this skill, provide:
1. **Paper Folder Path**: Directory containing paper files and data-check results

Paper folder must contain:
- `filter_result.json` (with `final_result.data_check_passed == true`)
- `repositories/` (cloned code repositories from data-check)
- `data/` (acquired data from data-check, organized per setting)
- `preprocessed/` (paper-preprocess output: `text.md`, `figures/`, `tables/`, `links.json`)
- `{paper_id}.pdf` and `{paper_id}.html` (original paper, for additional reference)

## Workflow

### Phase 1: Context Loading

1. Read `filter_result.json` and verify `final_result.data_check_passed == true`
2. Read [references/check_rules.md](references/check_rules.md) to understand all check definitions
3. Read `preprocessed/text.md` to understand the paper's content, methods, and evaluation
4. Examine `repositories/` code:
   - Locate entry scripts (train.py, main.py, run.py, etc.)
   - Locate data-loading code (dataset.py, dataloader.py, data.py, config files)
   - Grep for I/O patterns (`pd.read_`, `np.load`, `open(`, `load_dataset(`)
   - Understand Algorithm A's complete pipeline: data loading → [preprocessing] → training → evaluation
5. Read `preprocessed/figures/` to check for evaluation result presentations (learning curves, tables, etc.)

### Phase 2: Algorithm A Boundary Analysis

**Two complementary information sources**: code analysis and paper text. Use both to triangulate. When they conflict, the paper takes precedence as the authoritative expression of author intent (code may contain bugs, shortcuts, or partial implementations), but always document the discrepancy and cite both sources.

1. Extract A's definition from `task_info.algorithm`
2. **From the paper**: Read Methods/Data sections to understand what A is, what data it uses, how data was collected/prepared, and what A's contributions are.
3. **From the code**: Analyze the processing pipeline to identify what operations the code performs and which files it reads/writes. The code reveals A's implementation scope. Note: code loading patterns (e.g., `pickle.load()`) do not determine whether a component is external — a component loaded from a file may still be A's own output if the paper proposed it.
4. **Reconcile both sources** to establish the boundary between data (initial state) and algorithm operations. When paper and code disagree (e.g., paper describes a step as preprocessing but code implements it as part of A's pipeline), the paper takes precedence — document both perspectives and note the discrepancy.
5. Classify each data-related file in the repository:
   - `initial_state`: Raw data that existed before A started
   - `data_preparation`: Pre-A operations that transform raw data into the usable dataset; they define what the dataset is (still part of D_dev)
   - `algorithm_preprocessing_output`: Outputs of A's preprocessing (e.g., selected feature lists)
   - `algorithm_output`: A's training products (model weights, predictions, logs)
   - `external_resource`: External resources from other work that A depends on (pre-trained models, embeddings, knowledge bases, vocabularies, etc.)
   - `irrelevant`: Unrelated files (documentation, visualization scripts, etc.)

### Phase 3: Execute Checks V1-V5

Execute all five checks as defined in [references/check_rules.md](references/check_rules.md):

- **Check V1**: D_dev Component Boundary — are D_dev components all legitimate initial state?
- **Check V2**: Evaluation Setting Validity — are settings correctly identified (split/merge/remove)?
- **Check V3**: Separability Correctness — are split_procedure and extraction descriptions clean?
- **Check V4**: Data Directory Integrity — does data/ contain only initial state + D_eval?
- **Check V5**: Description & Evidence Consistency — do descriptions and evidence match reality?

### Phase 4: Output

Write all results to `{paper_folder}/data_verify_result.json`. See [references/output_schema.md](references/output_schema.md) for the complete schema.

## Judgment Principles

1. **Read-only**: Do not modify `filter_result.json`, data directories, or any existing files. Only write `data_verify_result.json`.
2. **Evidence required**: Every finding must cite concrete evidence (code path, file content, paper section).
3. **Actionable output**: Each finding should clearly describe the problem and what the recommended fix is, so a human reviewer can act on it.
4. **Conservative classification**: When uncertain whether a component is Algorithm A or data, document the ambiguity rather than guessing.
5. **Paper as authority**: When code and paper conflict, the paper takes precedence (see Phase 2). Always note the discrepancy and cite both sources.
6. **Completeness**: Check all evaluation settings (including rejected ones for V2). Report even minor issues — the human reviewer decides what to fix.
7. **Discrepancy triangulation**: When a value in filter_result.json disagrees with what is observed in actual files, do not assume either side is correct. Cross-reference all three sources (paper, code, actual data) to judge the root cause:
   - Papers commonly report approximate numbers (e.g., "~130,000 molecules", "approximately 200 features"). An approximate match between a paper-derived value and an actual file count is expected — not a finding.
   - Paper and code agree but data differs → likely data acquisition or processing error (the data is wrong, not filter_result.json).
   - Code and data agree but filter_result.json differs → likely an extraction error in filter_result.json.
   - Only report a finding when you have judged what is actually wrong and why. The finding should include this judgment, not merely list both values.
   - This principle applies to all checks (V1–V5) whenever comparing filter_result.json claims against observed reality — including numerical values, column names, file formats, and file existence.

8. **Do not invent issues**: If the `filter_result.json` and actual data align correctly and meet all criteria, do not force any findings. It is perfectly acceptable and expected to return an empty report when the existing data and records in `filter_result.json` are accurate. Do not make trivial stylistic changes to descriptions if their substantive meaning is correct.

## Output Files

```
{paper_folder}/
└── data_verify_result.json   # Verification report for human review
```
