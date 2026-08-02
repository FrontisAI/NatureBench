# NatureBench Leaderboard Submission Specification

This specification describes the files and information required to submit a
NatureBench run for leaderboard review.

## 1. Submission package

A submission contains three parts:

1. `submission.yaml`: submission and evaluation configuration.
2. `results.csv`: one row for each of the 90 official cases.
3. `raw-results/`: per-case result records and trajectories used for review.

## 2. `submission.yaml`

Use [`templates/submission.yaml`](templates/submission.yaml):

```yaml
submission:
  model: "Example Model"
  agent: "Example Agent"
  organization: "Example Organization"
  url: "https://example.org/project"
  submission_date: "2026-08-02"
  contact: "research@example.org"

evaluation:
  timeout_seconds: 14400
  web_search: false
  compute: "gpu_low: one NVIDIA RTX 4090 (24 GB); gpu_high: one NVIDIA A800 (80 GB); cpu: no GPU."
  judge_model: ""
  human_intervention: "none"
  deviations_from_reference: "none"
```

| Field | Requirement |
|---|---|
| `model` | Model name displayed on the leaderboard. |
| `agent` | Agent or harness name displayed on the leaderboard. |
| `organization` | Organization that ran and submitted the evaluation; independent submitters may use `Independent`. |
| `url` | Public link to the model, agent, paper, or project. |
| `submission_date` | Date the result package is submitted, in `YYYY-MM-DD` format. |
| `contact` | An email address, GitHub account, or another working contact method. |
| `timeout_seconds` | Per-task agent solve budget. The reference setting is 14,400 seconds. |
| `web_search` | Whether the agent uses web search during the evaluation. The reference setting is `false`. |
| `compute` | Short free-text description of the hardware assigned to tasks. The reference setup uses one NVIDIA RTX 3090/4090 (24 GB) for each `gpu_low` task, one NVIDIA A800 (80 GB) for each `gpu_high` task, and no GPU for `cpu` tasks. |
| `judge_model` | Submitter-side validity judge, if used. Leave empty if no judge was run. |
| `human_intervention` | Use `none` for autonomous runs; otherwise disclose the scope of human actions that could affect results. |
| `deviations_from_reference` | Use `none` or briefly describe changes to task coverage, evaluator, or other result-relevant settings. |

## 3. `results.csv`

The CSV has exactly these columns:

```csv
case_id,final_status,best_score,judge_verdict,judge_reason
```

| Field | Requirement |
|---|---|
| `case_id` | Official case ID. The file must contain all 90 IDs exactly once. |
| `final_status` | Final task status reported by the pipeline. |
| `best_score` | Best evaluator-produced aggregate improvement `g`. Keep the raw numeric value even when the submitter-side judge marks the task invalid. For no score, leave the field empty; do not use `-`, `None`, `none`, `null`, or `NaN`. |
| `judge_verdict` | Required. With a numeric score, use `valid` or `invalid`. Without a score, use `not_applicable`, as the pipeline does not normally judge unscored tasks; if a judge was run, report its `valid` or `invalid` verdict. |
| `judge_reason` | Required. For `valid` or `invalid`, copy the judge reason exactly. For `not_applicable`, write `not_applicable`. |

### Leaderboard metrics

The public metrics are calculated from the reviewed per-case rows.

- Score Rate (`SR`): tasks with a numeric score divided by 90.
- Completion Rate (`CR`): valid-scored tasks divided by 90.
- Match-SOTA: valid-scored tasks with `g >= 0`, divided by 90.
- Surpass-SOTA: valid-scored tasks with `g > 0.1`, divided by 90.
- Mean and median `g` over all tasks, with invalid and no-score cases assigned
  `g = -1`.
- Median `g` over valid-scored tasks.
- The metrics above, calculated separately for each domain.
- Score distribution across all tasks.

## 4. Raw results

**Required structure**

```text
raw-results/
├── run_summary.json             # optional
├── <case_id>/
│   ├── result.json
│   ├── submissions.jsonl
│   ├── judge_verdict.json       # required for valid/invalid verdicts
│   ├── trajectory.*             # one or more non-empty files
│   ├── workspace/               # optional
│   └── ...                      # optional additional audit artifacts
└── README.md                    # when format or review notes are needed
```

**Required records**

The official NatureBench pipeline produces the first three records below. Each
case must also include a trajectory or execution log.

- `result.json`: the task-level execution metadata.
- `submissions.jsonl`: the evaluator-attempt records. Scored attempts contain a
  numeric `aggregate_improvement`; an unscored task may have an empty file.
- `judge_verdict.json`: the validity-judge result, containing a Boolean
  `is_valid` field and a non-empty string `reason` field.
- `trajectory.*`: at least one readable, non-empty trajectory or execution log.
  The suffix and content format are unrestricted. The files should cover the
  complete history.

**Optional audit material**

`run_summary.json`, the final `workspace/`, and other audit material are not
required but may be included. The official pipeline retains only the final
workspace, not a snapshot for each evaluator attempt. If your agent or harness
retains per-attempt workspace snapshots and they can be shared, please include
them, especially the snapshot associated with the best attempt.

**Raw-results README**

Use `raw-results/README.md` to provide any context needed to understand and
review the submitted raw results. Include, as applicable:

- differences in file names, directory structure, fields, or execution behavior
  compared with the official pipeline;
- descriptions of any additional artifacts;
- notes needed to interpret the trajectory files;
- anything else maintainers should know when reviewing the results.

## 5. Result publication

### Pre-publication review

Maintainers will:

1. Validate the package and reconcile per-case scores with available result records.
2. Review trajectories and any additional audit artifacts, prioritizing unusually strong or anomalous cases.
3. Re-run the maintained validity judge when needed and resolve verdict differences.
4. Notify the submitter of the review outcome.

A submission may be rejected if the reported results cannot be traced to the supplied
artifacts or show evidence of result manipulation or fabricated records.

### Published result

For submissions that pass review, maintainers calculate the public metrics from
the reviewed per-case results using [`compute_scores.py`](compute_scores.py) and
add the result to the public leaderboard. The published entry may include the
model, agent, submitted URL, reviewed metrics, evaluation
configuration, and any disclosed deviations or audit limitations. Contact
information is used for review coordination and is not published.
