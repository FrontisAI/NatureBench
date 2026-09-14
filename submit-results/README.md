# Submit Results to the NatureBench Leaderboard

We welcome submissions from researchers and developers who have evaluated new
models or agents on NatureBench. All tracks use the same submission format,
validation tools, and review process.

## Choose a track

| Track | Track ID | Tasks |
|---|---|---:|
| Full | `full` | 90 |
| NatureBench-25 | `naturebench-25` | 25 |
| Cellular Omics | `cellular-omics` | 31 |
| Protein Biology | `protein-biology` | 16 |
| Biomedical Modeling | `biomedical-modeling` | 14 |
| Physical Modeling | `physical-modeling` | 13 |
| Molecular Design | `molecular-design` | 11 |
| Relational Reasoning | `relational-reasoning` | 5 |

Prepare one package per track, covering every official task in that track,
including failed, invalid, and no-score runs. To submit multiple tracks, prepare
a separate directory for each. The six domain tracks use the Full benchmark's
domain task sets.

## Prepare the submission

A submission directory contains:

```text
<submission-name>/
├── submission.yaml
├── results.csv
└── raw-results/
    ├── <case_id>/
    └── README.md              # when format or review notes are needed
```

From the repository root, generate the metadata template, result rows, and task list:

```bash
python submit-results/prepare_submission.py \
  --track full \
  --output-dir my-submission
```

Replace `full` with any track ID above. The command creates `submission.yaml`,
`results.csv`, and `tasks.txt` for the selected track.
Complete the `submission.yaml` and `results.csv`, and add the per-case `raw-results/`.

You can also start from [`templates/submission.yaml`](templates/submission.yaml)
and the existing [CSV templates](templates/).
See [`SUBMISSION_SPEC.md`](SUBMISSION_SPEC.md) for instructions on completing `submission.yaml` and `results.csv`, organizing the
per-case raw results, and the result review and publication process.

## Check the submission

From the repository root, run:

```bash
python submit-results/validate_submission.py \
  --metadata <submission-name>/submission.yaml \
  --results <submission-name>/results.csv \
  --raw-results <submission-name>/raw-results

python submit-results/compute_scores.py \
  --track <track-id> \
  --results <submission-name>/results.csv \
  --output <submission-name>/score_report.json
```

Use the same track ID as `evaluation.track` in `submission.yaml`.
The first command checks the submission format and the consistency of the
available result records according to `evaluation_pipeline`. For `custom`
pipelines, it only checks case coverage and non-empty raw artifacts.
The second command computes a preview of the public metrics and optionally
writes a standalone JSON report.

## Send the submission

Remove credentials and private endpoints, archive the directory, and send it
or a stable download link to **wangyuru@frontis.cn, zhangkaiyan@frontis.cn** with the subject:

```text
[NatureBench Result Submission] <agent> + <model>
```

Please include a short introduction and links to the model, agent, paper, or
project when available. Maintainers will review the artifacts, rerun the
validity judge when needed, and contact the submitter if more
information is required. Submissions that pass review are scored with
[`compute_scores.py`](compute_scores.py) and then added to the leaderboard.
