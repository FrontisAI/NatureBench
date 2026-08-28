# Task Packages and Task Lists

## Task Package Structure

```text
tasks/
    └── <case_id>/
        ├── problem/
        ├── evaluation/
        ├── environment/
        │   └── Dockerfile.v3
        ├── licenses/
        └── metadata.json
```

Task package fields:

| Field | Description |
|---|---|
| `problem/` | Agent-visible task instructions, input data description, and visible data. |
| `evaluation/` | `evaluator.py` and ground truth; the agent cannot directly access this directory. |
| `environment/Dockerfile.v3` | Task-specific environment, based on the base image defined by `docker/Dockerfile.base`. |
| `metadata.json` | Task name, domain, compute-resource demand, and per-instance SOTA scores. |

Some large tasks store visible data as `problem/data_archives/*.tar.gz` in the Hugging Face dataset. `run_naturebench.py` automatically extracts these archives after download so that every task exposes the same runtime path: `problem/data/`. After successful extraction, the local `problem/data_archives/`
directory is removed to avoid keeping a second copy of the same data.

## Task Lists

The root `task-set/` files define the 90-task Full track:

| File | Tasks | Description |
|---|---:|---|
| `cpu.txt` | 3 | Tasks that do not require a GPU. |
| `gpu_high.txt` | 17 | GPU tasks with higher memory or compute demand. |
| `gpu_low.txt` | 70 | GPU tasks with lower memory or compute demand. |
| `all.txt` | 90 | All tasks. |

`task-set/naturebench-25/` defines the 25-task track using the same resource groups:

| File | Tasks | Description |
|---|---:|---|
| `naturebench-25/cpu.txt` | 1 | Tasks that do not require a GPU. |
| `naturebench-25/gpu_high.txt` | 2 | GPU tasks with higher memory or compute demand. |
| `naturebench-25/gpu_low.txt` | 22 | GPU tasks with lower memory or compute demand. |
| `naturebench-25/all.txt` | 25 | All NatureBench-25 tasks. |
