# Phase 2: README Guide

## Objective

Generate `problem/README.md` — the task definition document that defines a standalone ML benchmark challenge extracted from the paper.

## Information Sources

1. **filter_result.json**: Use `task_info` as context — task_type, metrics (names, score_source), evaluation settings (names, descriptions, d_eval.x_test/y_ref definitions)
2. **`problem/data_description.md`**: Already-generated data documentation — ensure consistency in instance names, file references, and data descriptions
3. **Paper text/figures/tables**: For scientific background (Section 1) and metric definitions (Section 4)

## Critical Constraints

1. **No paper references**: Never mention paper title, authors, journal, DOI, or year. Write as a standalone challenge description.
2. **No algorithm names**: Never use the paper's proposed method name. The task invites NEW solutions.
3. **No method leakage**: Do not describe how the paper's algorithm works, which features it selects, what preprocessing it applies, or any implementation details.
4. **No hidden data description**: Never mention `evaluation/ground_truth/` or y_ref file details.
5. **No data_description.md references**: Do not add "See `data_description.md` for details" or similar cross-references.
6. **No evaluation internals**: Do not describe how the evaluator works, its validation logic, or its file reading mechanism.
7. **No build-time instructions**: Do not describe how the task package was constructed — e.g., how data was split, how oracles were extracted or re-implemented, how evaluation components were set up. The README describes the task as a standalone challenge, not its build process.
8. **Task-centric language**: Describe the PROBLEM and GOAL, not the paper's approach.
9. **Problem-centric naming**: Name the task after the Scientific Problem (e.g., "Protein Structure Prediction"), not the method name.

## Output Format

Generate `problem/README.md` following this structure:

````markdown
# [Task Name]

## 1. Scientific Problem
[1-2 paragraphs. Explain the scientific background and why this problem is important. Keep it human-readable and accessible.]

## 2. Task Objective
[Define the machine learning objective clearly and accurately.]
*   **Input**: [Describe the feature structure and content available to the solver]
*   **Output**: [Describe the target structure and content the solver must produce]

## 3. Dataset Information
[Brief description of dataset structure.]

## 4. Evaluation Metrics
### Primary Metric
*   **Name**: [Metric name]
*   **Definition**: [Brief explanation. Higher/lower is better.]

### Other Metrics
*   **[Metric Name]**: [Brief definition and direction]

## 5. Output Format

Each instance must produce a file at `output/{instance_name}/[FILENAME]`.

| Field | Value |
|-------|-------|
| **File** | `[FILENAME]` (e.g., `output.npy`, `output.csv`, `output.json`) |
| **Format** | [e.g., NumPy binary, CSV, JSON] |
| **Shape** | [e.g., (n_samples,), (n_samples, n_features)] |
| **Dtype** | [e.g., int64, float32] |
| **Values** | [e.g., integer cluster labels in [0, k-1], probabilities in [0, 1]] |

## 6. Submission Guidelines
We adopt the **"End-to-End Code Submission"** mode.
Your submission is a workspace directory containing code that performs the entire pipeline: loading data, preprocessing, training/inference, and saving results.

### Entry Point (`run.py`)
You must implement `workspace/run.py` as the entry script. Below is a starter template:

```python
import os

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "problem", "data"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "output"))

# Instance Definitions:
# [Populate with setting folder names and brief descriptions]
INSTANCES = [...]

def main():
    for instance in INSTANCES:
        data_path = os.path.join(DATA_DIR, instance)
        output_path = os.path.join(OUTPUT_DIR, instance)
        os.makedirs(output_path, exist_ok=True)

        # [TODO: Load data from data_path]
        # [TODO: Preprocess, train, infer]
        # [TODO: Save results to output_path]

if __name__ == "__main__":
    main()
```

### Notes
- You are responsible for the entire workflow: data loading, preprocessing, model training/inference, and saving output.
- You may create additional files in the workspace directory (e.g., `model.py`, `utils.py`) and import them in `run.py`.
- Data is read-only — do not modify files in `problem/data/`.
- Output must be saved to `output/{instance_name}/` in the format specified in Section 5.
````

## Content Guidelines

- **Task Name**:
  - Use the Scientific Problem as the name (e.g., "Protein Function Prediction")
  - No model/method names, no "Bench"/"Benchmark"/"Challenge" suffixes
- **Scientific Problem**:
  - Explain the domain-specific scientific context and why this problem is important
  - Keep it accessible but accurate
- **Task Objective**:
  - Define the ML objective; be specific about input/output data types and structures
  - Architecture-agnostic: describe what to achieve, not how
- **Dataset Information**:
  - Brief overview of structure and settings. Default to prose; only add a summary table when prose alone cannot convey the information clearly. Do NOT use tables to restate what prose already covers.
  - Do NOT repeat full schemas from data_description.md
- **Evaluation Metrics**:
  - Cross-reference `task_info.metrics` with the paper's results tables/text to select metrics. Only include metrics that are: (1) core to judging method quality (i.e., the primary metrics the paper uses to compare and rank methods), (2) well-defined and reproducible, and (3) have reported scores in the paper for **all** included evaluation instances **of the same task type**. Exclude auxiliary/secondary metrics and those the paper explicitly criticizes or notes as unreliable/misleading.
  - **Per-task-type metric grouping**: When instances span different task types (e.g., classification and regression), metrics naturally differ — each task type has its own metric set. In this case, list all metric sets and document which metrics apply to which instances. Within the same task type, only include metrics reported for all instances of that type; drop metrics reported for only a subset.
  - Choose exactly one **primary metric**: the metric most important for judging task success. Prefer the one the paper emphasizes most or treats as the main result (e.g., bolded in tables, discussed in text). When instances have different metric sets, choose one primary metric per task type.
- **Output Format**:
  - Choose file format and specify details based on y_ref alignment and structure:
    - y_ref is **order-aligned numeric** (per-sample labels/scores, no identifier column) → `.npy`. Specify: shape, dtype, value range.
    - y_ref is **keyed by identifier** (samples matched by an ID field) → `.csv`. Specify: ID column name (must match x_test), result column name(s) and dtype(s), whether header is included.
    - y_ref is **variable-length or nested** (lists of variable size, hierarchical/mixed-type structures) → `.json`. Specify: key structure with a brief example.
    - y_ref is a **single aggregate value** (one number per instance) → `.json`. Specify: key name, value type.
    - y_ref is a **domain object** (molecular structure, image, etc.) → domain format (`.pdb`, `.sdf`, `.png`, etc.). Specify: domain conventions.
- **Submission Guidelines**:
  - `INSTANCES`: Populate with `problem/data/` setting folder names. Single setting → `["default"]`.
  - Include task-specific notes in the Notes section as needed (e.g., "The number of clusters k is provided", "Handle varying input dimensions").

## Y_ref Type–Specific Guidance

The y_ref type (defined in data_organization_guide) affects how the README frames the task. Adapt the relevant sections accordingly:

| Y_ref Type | Task Objective | Output Format |
|------------|---------------|---------------|
| **Label** | "Predict Y for each test sample" | One prediction per test sample, aligned by order/ID with test set |
| **Oracle** | "Optimize X using the provided scorer/simulator" | Optimized solutions (parameters, structures, etc.) |
| **Distribution** | "Generate N samples satisfying [constraints]" — specify exact N matching the paper (distribution metrics are sample-size sensitive) | Set of N generated samples |
