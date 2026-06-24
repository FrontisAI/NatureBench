---
name: paper-filter
description: Filter CNS papers for suitability in extracting machine learning tasks. Uses a three-level cascade funnel (Task Nature → Evaluation System → Data Completeness) with progressive filtering; stops immediately upon rejection. Input is preprocessed paper data; output is the filtering decision result.
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, WebFetch, Bash(python *), Bash(python3 *)
---

# Paper Filter Skill

Filter CNS papers for machine learning task extraction suitability.

## Input Requirements

Before invoking this skill, provide:
1. **Paper Folder Path**: Directory containing original paper files and preprocessed data
2. **Output Directory**: Directory to store filtering results

Paper folder structure:
- `{paper_id}.pdf`: Original paper PDF file
- `{paper_id}.html`: HTML version of the paper
- `preprocessed/`: Preprocessed data subdirectory, containing:
  - `text.md`: Full paper text
  - `figures/`: Figures directory
  - `tables/`: Tables directory
  - `links.json`: List of links from the paper (with section identifiers and surrounding context)

## Supplementary Materials

`preprocessed/text.md` may not include supplementary content. When the main text references supplementary materials (tables, figures, or supplementary notes/text) for core results, metric details, evaluation protocols, or experimental details, and the information is not present in `preprocessed/text.md`:

1. Check `preprocessed/links.json` for supplementary material links (section: `supplementary_information`)
2. Download supplementary PDFs/files to a temporary location
3. Use the original paper PDF/HTML as fallback if supplementary links are not separately available
4. Extract relevant information (score tables, metric details, evaluation protocols, experimental details, and dataset descriptions)
5. **Delete** downloaded supplementary files after extraction is complete

## Workflow

### Phase 1: Understand Core Definitions

Read [references/core_definitions.md](references/core_definitions.md) to understand the basic criteria and requirements for task extraction.

Core definitions describe the structure of the candidate task tuple T = (A, Data, M, S, B):
- **A (Algorithm)**: The core algorithm or strategy proposed by the paper
- **Data**: The data environment involved in the task, divided into D_dev (development data) and D_eval (evaluation data)
- **M (Metric)**: The metric function used to measure result quality
- **S (SOTA)**: The performance values of the proposed core algorithm on evaluation metrics
- **B (Baseline)**: The baseline metric values reported in the paper (optional, may not exist)

Understanding these definitions helps accurately judge whether a paper satisfies various rules during filtering.

### Phase 2: Three-Level Cascade Filtering

Execute three-level filtering in order. **If ANY rule results in rejection, stop immediately** and do not proceed to the next rule or level.

During filtering, **extract task core information (task_info) while making judgments**, identifying and recording at each Level:

#### Level 1: Task Nature Filtering
Read [references/level1_rules.md](references/level1_rules.md), check:
- Rule 1.1: ML Task Extractability

Extract: task_type (task type), algorithm (algorithm name)

#### Level 2: Evaluation System Validity Filtering
Read [references/level2_rules.md](references/level2_rules.md), check:
- Rule 2.1: Performance Absoluteness
- Rule 2.2: Metric Determinism

Extract: metrics (list of metrics + score source), sota (method name), baseline (method list, may be empty)

#### Level 3: Data and Process Completeness Filtering
Read [references/level3_rules.md](references/level3_rules.md), check:
- Rule 3.1: Zero-Interaction Acquisition
- Rule 3.2: Initial State Completeness
- Rule 3.3: Evaluation Loop Completeness
- Rule 3.4: Data Consistency
- Rule 3.5: Partial Experiment Closure
- Rule 3.6: Data Scale Feasibility

Extract: data (d_dev + d_eval detailed information), size_tier

Level 3 verifies data availability and consistency using `scripts/validate_links.py` and data source inspection. Size estimation uses `scripts/estimate_size.py`.

### Phase 3: Output Validation and Results

Before writing the final output, perform a basic consistency check:

1. `task_info.algorithm` matches the algorithm described in filtering_process Rule 1.1
2. `task_info.metrics` matches `metrics_identified` in filtering_process Rule 2.1
3. `evaluation_settings` names and count match the settings recorded in filtering_process Rule 3.5
4. Every `url` in evaluation_settings has a corresponding entry in Rule 3.1 `links_checked`
5. No task_info field that should have been extracted is left empty (null or `[]` when content is expected)
6. `task_info.data.size_tier` matches Rule 3.6's `size_tier`; if size_tier is L or estimation_confidence is indeterminate, `final_result.passed` must be false

Fix any inconsistencies found, then output filtering results to `filter_result.json`. See [references/output_schema.md](references/output_schema.md) for format.

## Judgment Principles

1. **Binary Decision**: Each rule has only "pass" or "reject", no "partially compliant"
2. **Progressive Filtering**: Stop immediately upon rejection, record stopping point
3. **Reason Required**: Each judgment must provide specific reason and evidence
4. **Spirit over letter**: When a paper matches the pattern of a reject condition but not its exact wording, it should still be rejected
5. **Adversarial stance on Rule 1.1**: The default hypothesis is reject. The paper must affirmatively prove it belongs in scope. False negatives are cheap; false positives waste significant downstream effort.
6. **Paper text is ground truth**: Base all judgments on paper content, not assumptions

## Output Files

Upon completion, generate:

```
{output_dir}/
└── filter_result.json # Filtering decision result
```
