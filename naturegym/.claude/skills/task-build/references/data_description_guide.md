# Phase 1: Data Description Guide

## Objective

Generate `problem/data_description.md` — a detailed technical documentation of the physical data artifact in `problem/data/`.

## Information Sources

1. **filter_result.json**: Use `task_info.data` as context — pattern, evaluation settings (names, descriptions, d_dev/d_eval definitions, x_test/y_ref semantics, verification results)
2. **Physical inspection**: Verify and supplement by actually reading/inspecting the data files in `problem/data/`. Do NOT guess from filenames alone.

## Critical Constraints

1. **Describe only solver-visible data**: Document ONLY files in `problem/data/`. NEVER mention, describe, or hint at the existence of `evaluation/ground_truth/`.
2. **No paper references**: Do not reference the original paper, authors, journal, or methodology. Write as if the dataset is a standalone artifact.
3. **No method leakage**: Do not describe how the paper's algorithm uses the data. Describe the data objectively.
4. **No build-time instructions**: Do not describe how the data was acquired, split, reorganized, or how oracle/evaluation components were constructed. Describe the data as a standalone artifact, not its provenance or build process.
5. **Objective technical tone**: Focus on what the data IS (keys, shapes, types, content), not how to load or use it.

## Output Format

Generate `problem/data_description.md` following this structure:

```markdown
# Data Description

## 1. Directory Structure
[Clean tree view of `problem/data/` showing all setting directories and their files with brief annotations]

## 2. Dataset Overview
[1-3 paragraphs describing: what the dataset represents, the scientific context of the data (not the task), how settings relate to each other.]

## 3. File Formats & Schemas
[Organize by file type (if settings share the same format) or by setting (if formats vary), whichever is clearer]

### {File Pattern or Setting Group}
- **Format**: [e.g., CSV, HDF5, pickle, NPY, etc.]
- **Content Summary**: [1-2 sentences]
- **Fields/Columns**:
  - `field_name`: [Type, description, role — mark as INPUT or TARGET where applicable]

## 4. Special Notes
[Data-level caveats that affect correct interpretation or processing]
```

## Content Guidelines

- **Directory Structure**:
  - Annotate with shape/sample-count per file
  - When multiple settings share identical structure, show one fully and abbreviate the rest
- **Dataset Overview**:
  - Describe what the dataset represents and the scientific context of the data
  - Default to prose; only add a summary table when prose alone cannot convey the information clearly. Do NOT use tables to restate what prose already covers.
  - When `setting_dependencies` exists, describe the dependency objectively: which instance does not include a pretrained model and must obtain one by first training on another instance's data. This is a data-level fact about the initial state, not a method recommendation.
- **File Formats & Schemas**:
  - Inspect actual files to verify formats, column names, data types
  - Describe the file's content concisely
  - For files with many columns/keys/fields, group or list only critical ones
  - Mark fields as INPUT or TARGET where applicable — TARGET refers to training targets in D_dev, not hidden ground truth(`evaluation/ground_truth/`)
- **Special Notes**:
  - Document data-level caveats only: format anomalies, cross-setting inconsistencies, interpretation notes, alignment requirements
  - When cross-setting dependencies exist, note the training order constraint as a data-level caveat (e.g., "Instance X does not include a pretrained model; one must be obtained by training on Instance Y's data first")
  - Do NOT include preprocessing recommendations, method suggestions, or usage guidance.

## What NOT to Include
- No loading code examples
- No description of ground truth in `evaluation/ground_truth/`
- No paper methodology descriptions
- No references to `repositories/` or original codebase
- No cross-references to other task documents

