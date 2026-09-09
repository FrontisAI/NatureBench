---
name: task-build
description: Build a structured task package from a paper that has passed paper-preprocess, paper-filter, and data-check. Reorganizes data, generates problem description, evaluator, metadata, and environment Dockerfile.v3.
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash, WebFetch, Write, Edit
---

# Task Build Skill

Build a structured ML benchmark task package from a CNS paper that has completed the three preprocessing stages (paper-preprocess → paper-filter → data-check).

## Input Requirements

Before invoking this skill, provide:
1. **Paper Folder Path**: Directory containing the paper and all prior processing results
2. **Output Directory**: Where to build the final task package (can be same as paper folder or a new location)

Paper folder must contain:
- `{paper_id}.pdf` and `{paper_id}.html`: Original paper files
- `preprocessed/`: paper-preprocess output (`text.md`, `links.json`, `figures/`, `tables/`)
- `filter_result.json`: Combined output from paper-filter + data-check (must have `final_result.data_check_passed == true`)
- `data/`: Acquired data organized per setting (data-check output)
- `repositories/`: Cloned repositories (data-check output, reference only)

Paper folder may also contain:
- `data_verify_result.json` (optional): Independent verification report from data-verify. When present, use `algorithm_boundary.file_classifications` as supplementary reference for file role judgment (e.g., distinguishing algorithm artifacts from initial state, identifying external resources/oracles). When it conflicts with filter_result.json, verify against actual repository code and data to determine the correct classification.

## Output Structure

```
{output_dir}/
├── problem/                        # Solver-visible package
│   ├── data/                       # Solver-visible data
│   │   ├── {setting_1}/            # One directory per evaluation setting
│   │   │   ├── [d_dev files]       # Training data, validation data, pretrained models, etc.
│   │   │   └── [x_test files]      # Test inputs
│   │   └── {setting_2}/
│   │       └── ...
│   ├── data_description.md         # Technical data documentation
│   └── README.md                   # Task definition document
├── evaluation/                     # Evaluator package (hidden from solver)
│   ├── evaluator.py                # Automated evaluation script (reads from workspace/output/)
│   └── ground_truth/               # Reference answers
│       ├── {setting_1}/
│       │   └── [y_ref files]
│       └── {setting_2}/
│           └── [y_ref files]
├── environment/                    # Execution environment
│   ├── Dockerfile.v3               # Task-specific Docker image definition
│   └── packages.json               # Package manifest for automated verification
└── metadata.json                   # Task metadata and performance baselines
```

**NOTE**: `repositories/`, `preprocessed/`, `filter_result.json`, and paper PDF/HTML are NOT part of the final task package — they are working materials for building.

## Core Principles

### 1. Information Firewall
**CRITICAL**: The task package must not leak original paper information:
- **No paper references**: Never mention paper title, authors, journal, DOI, or publication year
- **No algorithm names**: Never use the paper's proposed method name (algorithm A name from task_info)
- **No method details**: Never describe how the original paper solves the task
- **No data usage patterns**: Never describe how the paper uses the data (which columns they selected, preprocessing choices, etc.)
- **No evaluation internals in solver-visible files**: Never expose evaluator logic or `evaluation/` paths in `problem/` files
- **Task-centric language**: Write as if defining a standalone ML challenge, not describing a paper

### 2. Iterative Consistency
The workflow is sequential, but consistency across all files is paramount:
- If a downstream step reveals an issue in an upstream document, **backtrack and fix**
- All files must be internally consistent (metric names, instance names, data paths, output formats)

### 3. Evidence-Based Construction
- filter_result.json is the primary guide. Consult paper and code for information it does not contain (scientific background, metric logic, scores), or when execution reveals contradictions with physical data
- Never fabricate or assume — report what is actually observed or confirmed

### 4. Phase-Gated Execution
Execute phases in order. At the end of each phase, summarize what was done and automatically proceed to the next phase. All phases (0-6) must be completed in a single execution.

### 5. Build Record
Maintain a `task_build` field in filter_result.json throughout all phases. If a setting is dropped in any phase, all subsequent phases must exclude it.

```json
"task_build": {
  "timestamp": "ISO 8601",
  "status": "success | pending_review | failed",
  "failure_reason": "string",

  "manual_review": [
    {
      "phase": "0 | 1 | 2 | 3 | 4 | 5 | 6",
      "description": "what needs human review and why"
    }
  ],

  "phase_0": {
    "dropped_settings": [
      {
        "setting": "setting name",
        "step": "0.3 | 0.5",
        "reason": "why this setting was dropped"
      }
    ],
    "merge_split_actions": [
      { "action": "merge|split", "source": ["..."], "result": ["..."], "reason": "..." }
    ],
    "completeness_fixes": [
      { "setting": "...", "component": "...", "action": "downloaded|copied|extracted", "detail": "..." }
    ],
    "cleanup_actions": [
      { "setting": "...", "files_removed": ["..."], "reason": "..." }
    ],
    "split_notes": [
      { "setting": "...", "note": "..." }
    ]
  },

  "phase_3": {
    "implementation": [
      {
        "metric": "metric name",
        "source": "author_adapted | library | manual",
        "detail": "e.g., adapted from repo evaluate.py L50-80, or sklearn.metrics.accuracy_score"
      }
    ],
    "verification": {
      "metric_logic": "passed | failed",
      "smoke_test": "passed | failed",
      "author_comparison": "passed | failed | not_available",
      "paper_reproduction": "passed | failed | not_feasible",
      "notes": "string | null"
    }
  },

  "phase_4": {
    "uncertain_tags": [
      { "field": "field path (e.g., tags.task_type)", "value": "chosen value", "reason": "why uncertain" }
    ],
    "missing_scores": [
      { "instance": "instance name", "detail": "what score is missing or ambiguous" }
    ],
    "notes": "string | null"
  },

  "phase_6": {
    "self_audit": {
      "task_definition": {
        "scientific_problem_accurate": "true | false",
        "task_objective_accurate": "true | false",
        "notes": "string | null"
      },
      "data_alignment": {
        "instances_match_paper_settings": "true | false",
        "data_content_matches_paper_description": "true | false",
        "notes": "string | null"
      },
      "metadata_tags": {
        "primary_domain": { "confidence": "high | medium | low", "notes": "string | null" },
        "workflow_topology": { "confidence": "high | medium | low", "notes": "string | null" },
        "methodology_paradigm": { "confidence": "high | medium | low", "notes": "string | null" },
        "compute_resources": { "confidence": "high | medium | low", "notes": "string | null" }
      },
      "performance_scores": {
        "all_scores_verified": "true | false",
        "notes": "string | null"
      }
    }
  }
}
```

- `status`: Set in Phase 6:
  - `success` = task package produced, no human intervention needed (some settings may have been dropped if unrecoverable)
  - `pending_review` = task package produced (possibly partial), but some issues need human verification or action (see `manual_review`)
  - `failed` = cannot produce a viable task package even with human intervention (see `failure_reason`)
- `manual_review`: Only present when `status == "pending_review"`. Exhaust all automated approaches before adding items. Each phase may add entries during execution.
- `failure_reason`: Only present when `status == "failed"`.
- **Notes**: Dropping some settings (including those needing manual review) does NOT block the build — all phases must proceed to completion with surviving settings. Only when **all** settings are dropped may the build terminate early (set `failed` and stop).
- `phase_0`: Data organization actions and dropped settings — sub-fields optional
- `phase_3`: Evaluator verification results — sub-fields required
- `phase_4`: Metadata generation issues — record uncertain tag choices and missing/ambiguous scores; sub-fields optional
- `phase_6`: Self-audit results — semantic quality checks performed during final verification; sub-fields required. Any item with `false` or `confidence == "low"` MUST be added to `manual_review`

## Workflow

### Prerequisites: Parse Context

Before any construction, build a holistic understanding of the task by reading `filter_result.json`, the original paper (`preprocessed/text.md`), and the repository code. filter_result.json is the primary structured guide; the paper and code supplement it with information it does not contain.

Understand:
- What is the task (task_type, algorithm, metrics, data pattern)
- Which evaluation settings passed
- How data is organized and how it should be split (separability info)
- What scores are reported and where (score_source)

**Terminology note**: filter_result.json uses "evaluation setting" to refer to each independent data/evaluation unit. In the final task package (README, evaluator), these are called "instances". The two terms refer to the same thing — each setting becomes one instance.

This step builds the holistic understanding needed across all phases. Do NOT proceed to Phase 0 until the task, data, and evaluation picture is clear.

### Phase 0: Data Organization
Read [references/data_organization_guide.md](references/data_organization_guide.md) for the complete guide.

**Summary**: Verify for setting merges/splits, check data completeness and remediate gaps, clean unnecessary files from `data/`, perform d_dev/d_eval separation and x_test/y_ref extraction, organize into `problem/data/` and `evaluation/ground_truth/`. Drop settings that cannot be completed.

### Phase 1: Data Description
Read [references/data_description_guide.md](references/data_description_guide.md) for the complete guide.

**Summary**: Generate `problem/data_description.md` — a technical documentation of the physical data artifact in `problem/data/`. Must be objective, paper-anonymous, and not describe private/ground_truth data.

### Phase 2: Task Definition (README) and Workspace Template
Read [references/readme_guide.md](references/readme_guide.md) for the complete guide.

**Summary**: Generate `problem/README.md` — defines the ML task, evaluation metrics, output format, dataset information, and submission guidelines. Must be paper-anonymous and task-centric.

### Phase 3: Evaluator
Read [references/evaluator_guide.md](references/evaluator_guide.md) for the complete guide.

**Summary**: Generate `evaluation/evaluator.py` — validates and scores output files against ground truth. Must be correct, tested, and reference author implementations where available.

### Phase 4: Metadata
Read [references/metadata_guide.md](references/metadata_guide.md) for the complete guide.

**Summary**: Generate `metadata.json` — structured metadata for task categorization and performance baselines.

### Phase 5: Environment
Read [references/environment_guide.md](references/environment_guide.md) for the complete guide.

**Mandatory known-issues grep pass**: after collecting the task's package list, before finalizing any version pins, `grep` every package name against the "Known compatibility notes and issues" section of `environment_guide.md`. A hit is **not advisory** — it prescribes the exact fix (version, install order, required `-dev` apt packages, tail-pin placement, etc.) and must be applied verbatim. Pay special attention to entries that specify mandatory placement ("final RUN", "last `RUN pip install`", "tail pin", "force-reinstall --no-deps") and to ecosystem-wide lock rules ("Torch ecosystem", "JAX ecosystem lock") — installing any ecosystem member triggers the whole chain's version pins.

**Summary**: Generate `environment/Dockerfile.v3` — defines the task's execution environment by inheriting from `naturebench-base:v3` and adding any missing dependencies.

### Phase 6: Final Verification
Perform end-to-end consistency checks and semantic self-audit:

1. **File Completeness**: Verify all required files exist
2. **Cross-file Consistency**:
   - Metric names: README ↔ evaluator ↔ metadata
   - Metric direction (higher/lower is better): README ↔ metadata
   - Instance names: README ↔ evaluator ↔ data_description ↔ actual `problem/data/` and `evaluation/ground_truth/` directories
   - Output format (file name, shape, dtype): README Section 5 ↔ evaluator validation logic
   - Ground truth paths in evaluator ↔ actual files in `evaluation/ground_truth/`
3. **Information Firewall Check**: Re-scan all generated documents for any paper/method information leakage. Ensure `problem/` files do not reference `evaluation/` paths.
4. **Self-Audit** — re-read the paper (`preprocessed/text.md`) and `filter_result.json`, then verify:
   - **Task definition**: Does README's scientific problem description accurately reflect the paper's research problem? Does the task objective correctly capture what the paper's evaluation measures?
   - **Data alignment**: Do the instances in `problem/data/` correspond to the evaluation settings described in the paper? Is the data scale (number of samples, features, etc.) consistent with what the paper reports?
   - **Metadata tags**: Re-evaluate each classification tag (`primary_domain`, `workflow_topology`, `methodology_paradigm`, `compute_resource_requirements`) against the paper. Assign confidence level (high/medium/low) for each.
   - **Performance scores**: Spot-check that `metadata.json` scores match the paper's tables/figures.
   - Record all results in `task_build.phase_6.self_audit`. Any item that is `false` or has `confidence == "low"` MUST be added to `manual_review` with a description of what needs human verification.
5. **Fix Issues**: If issues are found in steps 1-4, backtrack to the relevant phase and fix them
6. **Cleanup**: Remove any temporary files created during building
7. **Finalize Build Record**: Set `task_build.status` and `task_build.timestamp` in filter_result.json
