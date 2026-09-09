# NatureGym

**The automated pipeline that turns a published Nature-family paper into a containerized, runnable NatureBench task package.**

NatureGym standardizes papers with heterogeneous formats, toolchains, and data modalities into one reproducible task format, while imposing an information firewall that withholds the original method so that agents must *discover* solutions rather than reproduce them. It is the construction half of [NatureBench](../README.md).

The pipeline is **Skills-based**: each stage is a reusable skill (under `.claude/skills/` or `.agents/skills/`) invoked by an LLM agent (support Claude Code and Codex). Batch driver scripts (under `scripts/`) run a skill over many papers in parallel.

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
└── scripts/               # pipeline runners, batch drivers + helpers
    ├── batch_pipeline_main.py     # runs the construction pipeline without intermediate verification
    ├── batch_pipeline_verified.py # runs the construction pipeline with verification and repair
    ├── pipeline_runner.py         # shared orchestration for both pipeline scripts
    ├── batch_paper_preprocess_direct.py # runs paper-preprocess's scripts/ directly, without invoking an agent
    ├── batch_paper_preprocess.py   ├── batch_task_build.py
    ├── batch_paper_filter.py       ├── batch_task_verify.py
    ├── batch_filter_verify.py      ├── batch_task_fix.py
    ├── batch_data_check.py         ├── batch_dockerfile_verify.sh
    ├── batch_data_verify.py        ├── batch_dockerfile_fix.py
    ├── batch_filter_verify_correction.py # invokes verify-apply for filter results
    ├── batch_data_verify_correction.py   # invokes verify-apply for data results
    ├── batch_target_utils.py
    ├── docker_env_verify.py       # run inside the Docker image by batch_dockerfile_verify.sh
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

With the `naturegym` environment active, run commands from this NatureGym directory. The scripts accept a parent directory of per-paper folders, each containing one paper's PDF and HTML. Replace `./papers` in the examples below with your own directory path.

### Run stages individually

Load the desired skill in Claude Code or Codex and provide the paper directory, or use its corresponding batch script below. Follow the Pipeline order and pass conditions when choosing the next step.

```bash
cd naturegym

# Run a skill over multiple papers, or one selected paper.
python scripts/batch_paper_preprocess.py ./papers -j 4
python scripts/batch_paper_filter.py --single ./papers/paper_001

# Build and verify one task's Docker environment.
bash scripts/batch_dockerfile_verify.sh --single paper_001 ./papers
```

Agent-based scripts accept `--agent claude|codex` (default: `claude`). Each script also accepts --single <folder> for one paper and --start N --end N for a subfolder range. Use each script's `--help` for Python driver options; Docker shell options are listed in its header.

### Run the whole pipeline

NatureGym provides two scripts for running the construction pipeline end to end, with or without intermediate verification and repair:

| Workflow | Processing | Docker verification default |
|---|---|---|
| **Main** | Preprocess → Filter → Data check → Task build | Off |
| **Verified** | Main stages with verification and repair | On |

```bash
# Main workflow
python scripts/batch_pipeline_main.py ./papers -j 4

# Verified workflow
python scripts/batch_pipeline_verified.py ./papers -j 4

# Resume a previous run
python scripts/batch_pipeline_verified.py ./papers -j 4 --resume
```

Both scripts accept the following options; `--max-fix-rounds` applies only to the Verified workflow.

| Option | Purpose |
|---|---|
| `--docker` / `--no-docker` | Enable or skip Docker verification and repair in either workflow |
| `--max-fix-rounds N` | Cumulative repairs per paper, per filter/data/task verification stage; default `2` |
| `--docker-max-fix-rounds N` | Independent Docker repair limit; default `2` |
| `--resume` | Resume at the interrupted stage and continue the remaining steps |
| `--dry-run` | Preview selected papers and stages without executing |

Set either repair limit to `0` to verify without fixing. Use `--help` for Python driver options.

**Resume**

- **Recover from interruption:** use `--resume` with the same workflow and saved state to continue from an interrupted stage or execution error, skipping completed steps.
- **Allow more repair attempts:** if verification still fails after the repair limit is reached, combine `--resume` with a higher `--max-fix-rounds` (or `--docker-max-fix-rounds` for Docker). Previously started fixes count toward the new total: 2 used fixes with a new limit of 4 allow 2 more.

**Saved results**

- **Progress CSV:** `<input>/pipeline_status.csv` contains one row per paper, recording completion(`completed=true` means processing ended, including rejection), the last completed stage (`current_stage`), the ending stage (`end_stage`) and each stage's result/status. For a batch, it is saved in the parent directory; with `--single`, inside the paper directory. Override the location with `--state-file`.
- **Task outputs:** generated files stay inside each paper directory, including `preprocessed/`, `filter_result.json` and the task package (`problem/`, `evaluation/`, `environment/`, `metadata.json`).
- **Pipeline events:** `logs/pipeline_events.jsonl` records scheduling events and repair counts; Keep this file and the CSV to resume a run.
