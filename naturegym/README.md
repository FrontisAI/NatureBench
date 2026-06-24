# NatureGym

**The automated pipeline that turns a published Nature-family paper into a containerized, runnable NatureBench task package.**

NatureGym standardizes papers with heterogeneous formats, toolchains, and data modalities into one reproducible task format, while imposing an information firewall that withholds the original method so that agents must *discover* solutions rather than reproduce them. It is the construction half of [NatureBench](../README.md).

The pipeline is **Skills-based**: each stage is a reusable [Claude Code](https://docs.claude.com/en/docs/claude-code) skill (under `.claude/skills/`) invoked by an LLM agent. Batch driver scripts (under `scripts/`) run a skill over many papers in parallel.

## Pipeline

```
Raw paper (PDF + HTML)
   │
   ▼
[1] paper-preprocess      figures/tables, Markdown, link extraction
   │                       
   ▼
[2] paper-filter          Level 1 task / Level 2 evaluation / Level 3 data
   │   ├─ filter-verify     adversarial re-check
   │   └─ verify-apply      apply corrections back into filter_result.json
   ▼  (passed == true)
[3] data-check            repo clone, data acquisition, Algorithm-A boundary, deep verification
   │   ├─ data-verify       independent read-only check
   │   └─ verify-apply      apply corrections
   ▼  (data_check_passed == true)
[4] task-build            data organization, task documentation, evaluator, metadata, environment
   │   ├─ task-verify       36 static + dynamic checks
   │   └─ task-fix          repair failed checks (iterative)
   ▼  (task_build.status == "success")
[5] Dockerfile verify/fix  build the image on a real machine, verify imports/versions
   │   ├─ scripts/batch_dockerfile_verify.sh   Docker build + import smoke test
   │   └─ dockerfile-fix         repair Docker build / import failures
   ▼
Runnable task package: problem/ + evaluation/ + environment/ + metadata.json
```

A shared per-paper record, `filter_result.json`, flows through the pipeline: every stage reads and updates it, accumulating the task tuple `T = (A, D, M, S, B)` — core algorithm, dataset, metric, SOTA score, and optional baseline.

## Skills

| Stage | Skill | Function |
|---|---|---|
| 1 | `paper-preprocess` | PDF/HTML → Markdown text, figure/table screenshots, classified link list |
| 2 | `paper-filter` | Three-level feasibility filter; extracts the task tuple into `filter_result.json` |
| 2 | `filter-verify` | Adversarial re-check of the filtering decision and extracted task info |
| 3 | `data-check` | Clone repos, acquire data, determine the Algorithm-A boundary, deep data verification |
| 3 | `data-verify` | Independent read-only verification of the data components |
| 4 | `task-build` | Assemble the task package (data, task brief, evaluator, metadata, Dockerfile) |
| 4 | `task-verify` | 36 checks across file completeness, consistency, firewall, design, dynamic testing |
| 4 | `task-fix` | Repair issues found by `task-verify`, following `task-build` rules |
| 5 | `dockerfile-fix` | Diagnose and fix Docker build / import failures |
| — | `verify-apply` | Apply `filter-verify` / `data-verify` corrections back into `filter_result.json` |

## Layout

```
naturegym/
├── .claude/skills/        # the 10 construction skills
│   ├── paper-preprocess/   ├── data-check/      ├── task-verify/
│   ├── paper-filter/       ├── data-verify/     ├── task-fix/
│   ├── filter-verify/      ├── task-build/      └── dockerfile-fix/
│   └── verify-apply/
└── scripts/               # batch drivers + helpers
    ├── batch_paper_preprocess.py   ├── batch_task_build.py
    ├── batch_paper_filter.py       ├── batch_task_verify.py
    ├── batch_filter_verify.py      ├── batch_task_fix.py
    ├── batch_data_check.py         ├── batch_dockerfile_verify.sh
    ├── batch_data_verify.py        ├── batch_dockerfile_fix.py
    ├── batch_target_utils.py       └── docker_env_verify.py
    └── ...
```

## Requirements

- The **`naturegym` construction environment** (Python 3.11), separate from the evaluation environments. Create and activate it with:
  ```bash
  conda env create -f naturegym/environment.yml
  conda activate naturegym
  ```
- Docker, for stage 5 (image build + import verification). Task images inherit from `naturebench-base:v3` (built from `../docker/Dockerfile.base`).

## Running

With the `naturegym` environment active, each batch driver runs one stage over a parent directory of per-paper folders, in parallel with `-j`. Run them **from the `naturegym/` directory** so the agent discovers the skills under `.claude/skills/`:

```bash
cd naturegym

# [1] preprocess every paper folder under ./papers
python scripts/batch_paper_preprocess.py -j 4 ./papers
```

Each script also accepts `--single <folder>` for one paper and `--start N --end N` for a subfolder range (`python scripts/batch_paper_filter.py --help`).

Stages are gated: a paper proceeds only when the previous stage records success in `filter_result.json` (`passed`, then `data_check_passed`, then `task_build.status == "success"`). The construction is agent-driven and the reviews surface critical corrections for human confirmation.

