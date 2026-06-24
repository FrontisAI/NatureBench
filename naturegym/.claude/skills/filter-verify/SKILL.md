---
name: filter-verify
description: Verify paper-filter results by checking pass/reject judgment correctness, validating task_info field accuracy, and detecting internal inconsistencies. Outputs actionable corrections to filter_result.json.
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Write
---

# Filter-Verify Skill

Verify filter_result.json produced by paper-filter. Three core responsibilities:
1. Check whether the pass/reject judgment is correct
2. Validate that task_info fields are accurate and complete
3. Produce an actionable corrections list to drive filter_result.json updates

## Input Requirements

Paper directory must contain:
- `preprocessed/text.md`: Full paper text
- `preprocessed/links.json`: Extracted links
- `preprocessed/figures/`: Extracted figures and tables
- `filter_result.json`: paper-filter output

## Context

The pipeline extracts ML tasks from papers to build benchmark challenges. The goal is not to reproduce the paper's algorithm — it is to test whether an AI agent (the "Solver") can independently solve the same ML problem using any method, potentially surpassing the original. The Solver receives the same initial data as the paper's authors, without knowing the paper or its algorithm. Its results are scored against ground truth using the paper's metrics, with the paper's reported scores as baselines for comparison. The benchmark must be fair: include all legitimate initial data (excluding any would make the task unfairly harder) while withholding Algorithm A's outputs (including any would leak solutions). filter-verify ensures only papers with genuine algorithmic innovation space and meaningful baselines enter the pipeline.

## Workflow

### Phase 0: Load & Summarize

1. Read `filter_result.json` in full
2. Read [references/check_rules.md](references/check_rules.md)
3. Read [references/output_schema.md](references/output_schema.md)
4. Read `preprocessed/text.md` in full
5. Read `preprocessed/links.json`
6. Scan `preprocessed/figures/` for main result tables and figures

Extract and record the following from the paper text (NOT from filter_result.json):
- What the paper's core contribution is
- What Algorithm A is (the method proposed by the authors in this paper)
- Which tables/figures contain main results, what metrics each uses, and which datasets are covered
- The evaluation method used (fixed split / random split / K-fold CV)

Based on the above, write a `paper_summary` (3-5 sentences) covering:
- What problem the paper addresses
- What method is proposed (Algorithm A)
- What data and metrics are used for evaluation
- Key conclusions

This summary is written to the `paper_summary` field in the output, helping downstream stages quickly understand the paper.

### Phase 1: Judgment Verification (C1-C3)

Apply checks C1, C2, C3 as defined in check_rules.md to verify whether the pass/reject judgment is correct.

**Key principle**: Do not ask "does the original reasoning sound plausible?" Instead ask "would this paper survive scrutiny from an adversarial reviewer who wants to reject it?"

### Phase 2: Task Info Verification (C4-C10)

Apply checks C4-C10 as defined in check_rules.md to verify task_info field correctness.

For each error found: specify the JSON path, current value, recommended value, and paper evidence.

### Phase 3: Output

Write results to `verification_result.json` in the paper directory. See [references/output_schema.md](references/output_schema.md) for the format.

## Judgment Principles

1. **Adversarial stance on Rule 1.1**: The default hypothesis is reject. The paper must affirmatively prove it belongs in scope. The pipeline has far more papers than needed; false negatives are cheap, false positives waste significant downstream effort.

2. **Spirit over letter**: When a paper matches the described pattern of a reject example but not its exact wording, it should still be rejected.

3. **Algorithm A litmus test**: Ask "if an ML researcher received D_dev and D_eval, what would they change to beat SOTA?" If the answer involves improving the model/architecture/loss/training method → there is algorithmic innovation space. If the answer is to collect better data/change physical equipment/modify experimental setup → no algorithmic innovation space.

4. **SOTA must be challenging**: Algorithm A must achieve competitive quality performance (at or above the best baseline). If A's quality scores are not competitive (e.g., A focuses on efficiency and sacrifices quality), the reported SOTA S does not represent the quality frontier and cannot serve as a meaningful benchmark.

5. **Act on findings**: Every issue must produce a concrete correction (path + recommended value). Documentation-only findings are not accepted.

6. **Paper text is ground truth**: Verify whether filter_result.json content is consistent with the paper, not whether filter_result.json is internally self-consistent.

7. **Complete evaluation settings coverage**: If the paper's main result tables report N datasets, evaluation_settings + rejected_settings must cover all N. Missing entries are errors.

8. **Do not invent issues**: If the original `filter_result.json` is completely accurate and no issues are found, do not force any changes. It is perfectly acceptable and expected to return an empty corrections list when the records in `filter_result.json` is correct. Do not make trivial stylistic changes (e.g., rephrasing a correct summary).
