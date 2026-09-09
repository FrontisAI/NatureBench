# Phase 4: Metadata Guide

## Objective

Generate `metadata.json` — structured metadata for task categorization, domain classification, and performance baselines.

## Information Sources

1. **filter_result.json**: `task_info` (task_type, algorithm, metrics, sota, baseline, dependencies), evaluation settings
2. **`problem/README.md`**: Task name, metric definitions (names, primary/secondary, direction), instance names
3. **`evaluation/evaluator.py`**: Metric names (must match exactly)
4. **Paper text/figures/tables**: Scientific domain, compute resources, performance scores from tables/figures referenced in `task_info.metrics[].score_source`

## Output Format

Generate `metadata.json` at the task package root:

```json
{
  "task_name": "Task Name String (must match README title)",
  "workflow_topology": "strict_single_step | serial_pipeline | multi_task_parallel | pretrain_finetune",
  "methodology_paradigm": "domain_specific_tooling | general_ml_application | other",
  "tooling_metadata": {
    "interaction_level": "level_1_python_lib | level_2_cli_engine | level_3_gui | null",
    "main_tools": [
      {
        "name": "Tool Name",
        "purpose": "Why is it used?",
        "interaction_type": "level_1_python_lib | level_2_cli_engine | level_3_gui"
      }
    ]
  },
  "domain_metadata": {
    "primary_domain": "Mathematics | Physics | Computer Science | Biology | Medicine | Materials Science | Chemistry | Other",
    "sub_domain": "String (1-3 words)",
    "domain_tags": ["keyword1", "keyword2", "keyword3"]
  },
  "compute_resource_requirements": {
    "cpu_compute": {
      "severity": "low | medium | high",
      "quantity_text": "String"
    },
    "gpu_compute": {
      "severity": "none | low | medium | high",
      "quantity_text": "String"
    },
    "runtime": {
      "severity": "short | moderate | long",
      "quantity_text": "String"
    }
  },
  "performance_entries": [
    {
      "dataset_name": "Instance/Dataset Name (must match README instance names)",
      "metrics": [
        {
          "name": "MetricName (MUST match README and evaluator)",
          "is_primary": true,
          "metric_direction": "higher_is_better | lower_is_better",
          "source_description": "Table X or Figure Y",
          "unit": "% | Angstroms | null",
          "sota_score": [{ "value": "95.5 ± 0.2", "method": "VariantA" }],
          "baseline_score": { "value": "88.0", "method": "MethodName" }
        }
      ]
    }
  ]
}
```

## Field Definitions

**Note**: `workflow_topology`, `methodology_paradigm`, `tooling_metadata`, `domain_metadata`, and `compute_resource_requirements` are all classified based on the paper's proposed algorithm A.

### workflow_topology

Classify the structural complexity of the inference pipeline:
- `strict_single_step`: Single Input → Model → Output (standard supervised learning)
- `serial_pipeline`: Step A Output → Step B Input → Final Output (errors propagate)
- `multi_task_parallel`: Single Input → Branch A & Branch B (different outputs)
  - **IS**: Algorithm A's architecture has parallel output branches producing structurally different outputs in one forward pass (e.g., segmentation mask + activity traces, image translation + cell classification)
  - **IS NOT**: Same algorithm evaluated on different datasets/instances (use `strict_single_step`)
  - **IS NOT**: Single output evaluated by multiple metrics (use `strict_single_step`)
  - **IS NOT**: Multi-label classification / multi-target regression / multi-objective optimization — outputs are homogeneous (same type), just multi-dimensional (use `strict_single_step`)
- `pretrain_finetune`: Distinct pre-training stage → fine-tuning stage

### methodology_paradigm

Classify the core "engine" of the proposed method:
- `domain_specific_tooling`: The workflow **relies** on specialized scientific software, physical simulators, or domain-specific libraries to generate features, label data, or validate results.
  - **Crucial Rule**: Standard ML stack (PyTorch, TensorFlow, JAX, Scikit-learn, Numpy, Pandas, Matplotlib) does **NOT** count as domain-specific tooling.
  - **Indicator**: If removing the external tool/library makes the core task impossible (e.g., calculating quantum energy, aligning genomic sequences), choose this.
- `general_ml_application`: Standard ML frameworks only. The workflow is mathematically self-contained.
- `other`: Pure wet-lab experiments or theoretical derivation without a data-driven ML component.

### tooling_metadata

Only populate if `methodology_paradigm == "domain_specific_tooling"`, else set to `null`.
- `interaction_level`: Highest difficulty among all tools (Level 3 > Level 2 > Level 1)
  - `level_1_python_lib`: Specialized domain libraries installable via `pip`/`conda`, called via `import`. Data exchange in RAM. Examples: RDKit, Scanpy, ASE, Biopython.
  - `level_2_cli_engine`: Standalone binaries executed via CLI/shell. Requires file I/O and `subprocess.run()`. Examples: GROMACS, VASP, AutoDock Vina, BLAST.
  - `level_3_gui`: Software requiring GUI or manual visual interaction. No documented CLI/API. Examples: ImageJ (manual), CryoSPARC (Web UI).

### domain_metadata

- `primary_domain`: Choose from: Mathematics, Physics, Computer Science, Biology, Medicine, Materials Science, Chemistry, Other. If cross-domain, choose the **application problem** domain (e.g., AI applied to Biology → Biology).
- `sub_domain`: 1-3 words describing the specific sub-field (e.g., "Protein Folding", "Fluid Dynamics").
- `domain_tags`: 3-5 keywords representing methods, objects of study, or key concepts.

### compute_resource_requirements

Analyze resources required to reproduce the method (prioritize inference/evaluation; if training is the main contribution, describe training resources).

- **cpu_compute**:
  - `severity`: `low` (≤32 cores, personal machines), `medium` (32-128 cores, workstation/server), `high` (>128 cores, HPC/cluster)
  - `quantity_text`: Specific mentions from paper (e.g., "2x Intel Xeon Gold", "50 nodes")
- **gpu_compute**:
  - `severity`: `none` (0 GPUs), `low` (1 GPU), `medium` (2-8 GPUs, single node), `high` (>8 GPUs, multi-node)
  - `quantity_text`: GPU model and count (e.g., "1x A100", "8x V100", "0 GPUs")
- **runtime**:
  - `severity`: `short` (<1h), `moderate` (1-24h), `long` (>24h)
  - `quantity_text`: Execution time mentions (e.g., "Training took 3 days", "Inference takes 5ms per sample")
- **Inference for missing data**: For any of the three fields above (`cpu_compute`, `gpu_compute`, `runtime`), if not explicitly stated in the paper, infer from method complexity, data volume, and model architecture. Mark inferred values in `quantity_text` (e.g., "~2 hours (estimated based on ...)").

### performance_entries

One entry per evaluation instance/dataset.

- **dataset_name**: Must match instance names used in README/evaluator (i.e., `problem/data/` folder names)
- **metrics**: Must list all metrics applicable to this instance as defined in README — names must match exactly. When README defines per-task-type metric sets, list only the metrics for this instance's task type. The union of metrics across all performance_entries must equal the full metric set in README.
  - `name`: Must match README and evaluator exactly
  - `is_primary`: `true` only for the primary metric defined in README
  - `metric_direction`: `higher_is_better` or `lower_is_better`
  - `source_description`: Paper location where scores appear (e.g., "Table 2", "Figure 3")
  - `unit`: Unit of measurement (e.g., "%", "Å", "kcal/mol", or `null` if unitless). Verify from table headers, captions, or domain knowledge.
- **Score Definitions**:
  - `sota_score`: The paper's proposed method (algorithm A) scores. If algorithm A has named variants, list ALL variants as an array: `[{ "value": "95.5", "method": "VariantA" }, { "value": "94.8", "method": "VariantB" }]`. Single variant uses the same array format with one element.
  - `baseline_score`: The most representative baseline method's score. `{ "value": "score string", "method": "method name" }`. Use the same baseline method across instances when possible; only vary if a method is absent for a specific instance. Set to `null` if no baseline is reported in the paper.
  - **Variance**: Capture the full string including variance (e.g., "95.5 ± 0.2"). Do NOT drop the ± part. **Crucial**: Use the literal `±` character instead of the Unicode escape `\u00b1`.
- **Score extraction**:
  - Locate the score source referenced in `task_info.metrics[].score_source`:
    1. **First, search preprocessed/text.md**: Look for the referenced table/figure number. Many tables are converted to markdown format in text.md. If found and scores are readable, extract from there.
    2. **If not in text.md or unclear, check image files**: Look in `preprocessed/figures/` or `preprocessed/tables/` for the corresponding image file and extract visually.
  - For figures with sub-panels (a, b, c...), identify the correct sub-panel from the caption. Prefix values read from figures with `~` to indicate approximate (e.g., `"~0.97"`).
  - If exact values are not in main text, download supplementary materials from links in `preprocessed/links.json` (section: `supplementary_information`) and check. Delete downloaded supplementary files after extraction.
  - If still unavailable, leave the value as `null` — do NOT guess or approximate.

## Correctness Checks (CRITICAL)

Before finalizing metadata.json:

1. **Metric name consistency**: All metric `name` fields must exactly match README and evaluator output keys
2. **Instance coverage**: One performance_entry per task instance
3. **Score accuracy**: Cross-check extracted scores against paper tables/figures
4. **Direction correctness**: Verify higher_is_better vs lower_is_better for each metric
5. **Label correctness**: Verify domain classification, workflow topology, and paradigm
6. **Valid JSON**: No trailing commas, correct types

## Build Record

Record issues in `task_build.phase_4`: uncertain tag choices (`uncertain_tags`), missing or ambiguous scores (`missing_scores`), and other notes.
