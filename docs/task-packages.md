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

## Task Lists

`task-set/` lists are divided by resource demand:

| File | Tasks | Description |
|---|---:|---|
| `cpu.txt` | 3 | Tasks that do not require a GPU. |
| `gpu_high.txt` | 17 | GPU tasks with higher memory or compute demand. |
| `gpu_low.txt` | 70 | GPU tasks with lower memory or compute demand. |
| `all.txt` | 90 | All tasks. |
