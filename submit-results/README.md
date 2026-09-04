# Submit Results to the NatureBench Leaderboard

We welcome submissions from researchers and developers who have evaluated new
models or agents on NatureBench. Follow the format below so the results can be
reviewed and compared with existing entries.

## What to submit

Prepare one directory containing:

```text
<submission-name>/
├── submission.yaml
├── results.csv
└── raw-results/
    ├── <case_id>/
    └── README.md              # when format or review notes are needed
```

Start from [`templates/submission.yaml`](templates/submission.yaml). Use
[`templates/results.csv`](templates/results.csv) for the 90-task Full track or
[`templates/results_naturebench_25.csv`](templates/results_naturebench_25.csv)
for NatureBench-25. See [`SUBMISSION_SPEC.md`](SUBMISSION_SPEC.md) for
instructions on completing `submission.yaml` and `results.csv`, organizing the
per-case raw results, and the result review and publication process.

## Check the submission

From the repository root, run:

```bash
python submit-results/validate_submission.py \
  --metadata <submission-name>/submission.yaml \
  --results <submission-name>/results.csv \
  --raw-results <submission-name>/raw-results

python submit-results/compute_scores.py \
  --track <full-or-naturebench-25> \
  --results <submission-name>/results.csv \
  --output <submission-name>/score_report.json
```

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
