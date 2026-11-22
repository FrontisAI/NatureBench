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

Prepare three items for the selected track.

- `submission.yaml` describes the evaluation setup, including any differences
  from the reference setup. Commit it in the PR.
- `results.csv` records one result per official task, including failed, invalid,
  and unscored runs. Commit it in the PR.
- `raw-results/` contains the per-case records and trajectories. Include
  `raw-results/README.md` when the format or results need explanation. Package
  this directory separately and share its download link as described below.

From the repository root, generate the starter YAML, CSV, and task list.

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

To check just the two public files, replace `--raw-results <path>` with `--public-only`.

## Open a submission PR

1. Fork `FrontisAI/NatureBench` or sync your existing fork with the upstream
   `main` branch. Create a branch for your submission from `main`.
2. Add `submission.yaml` and `results.csv` under
   `submissions/<track>/<submission-id>/`. Use a unique lowercase,
   hyphen-separated submission ID. Commit the two files, push your branch to
   your fork, and open a PR targeting `FrontisAI/NatureBench:main`.
3. In the PR description, list the agent, model, track, and submission directory.
   Share the raw-results archive using one of these options.
   - **Public download.** Put the download link in the PR description.
   - **Private download.** Write “Shared privately by email” in the PR
     description. Grant the maintainers access and email the download link,
     PR URL, and corresponding commit to
     **wangyuru@frontis.cn, zhangkaiyan@frontis.cn**.
4. To address feedback, push changes to the same branch in your fork. If the
   archive changes, update the PR description or reply to the original email
   with the new link and the corresponding commit.

## Review and publication

We review the raw results and explain any issues in the PR. For accepted
submissions, we confirm the final results and add them to the leaderboard.
