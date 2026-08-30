# NatureBench on Harbor

This directory contains the code needed to run NatureBench tasks with Harbor.
Prebuilt Harbor tasks are available in the
[`FrontisAI/NatureBench-Harbor`](https://huggingface.co/datasets/FrontisAI/NatureBench-Harbor)
dataset.

## Contents

| Path | Purpose |
|---|---|
| `adapter/` | Converts source NatureBench tasks into Harbor task packages. |
| `extensions/` | Provides NatureBench extensions for agent timing and Docker GPU support. |
| `images/naturebench-base/` | Builds `naturebench-base:v3`, inherited by task main containers. |
| `images/naturebench-eval-main/` | Builds `naturebench-eval:main`, inherited by task evaluation sidecars. |
| `scripts/build_images.sh` | Builds both NatureBench images. |
| `scripts/download_tasks.py` | Downloads harbor tasks from Hugging Face. |
| `run.yaml` | Reference Harbor configuration. |

## Adapter

The adapter converts original NatureBench tasks into the Harbor task format.
It is intended for dataset maintainers; the Harbor tasks published on Hugging
Face have already been converted and are ready to use.

```bash
cd /path/to/NatureBench
python -m pip install -e ./harbor/adapter

naturebench-to-harbor \
  --source-root /path/to/source-tasks \
  --output-dir /path/to/harbor-tasks
```

Convert selected tasks with `--task-ids`:

```bash
naturebench-to-harbor \
  --source-root /path/to/source-tasks \
  --output-dir /path/to/harbor-tasks \
  --task-ids <task-id> [<task-id> ...]
```

Existing output tasks are not overwritten unless `--overwrite` is supplied.

For each task, the adapter copies the input data, evaluator, metadata, and
licenses; then renders `task.toml`, `instruction.md`, the main-container
Dockerfile, Docker Compose configuration, evaluation sidecar, and separate verifier.

## Extensions

This package provides the two Harbor extensions required by the NatureBench protocol:

- `naturebench_extensions.timed_agent:NatureBenchTimedAgent` wraps a
  Harbor agent, starts the task timer when the inner agent starts, and
  enforces an effective solve-time budget that excludes `/evaluate` runtime.
- `naturebench_extensions.docker_environment:NatureBenchDockerEnvironment`
  reuses Harbor's local Docker environment and declares GPU support.

**`NatureBenchTimedAgent`**:

It consumes `inner_agent` and `timeout`; all other agent
kwargs are forwarded to the selected inner agent.

The wrapper uses NatureBench's default `timeout` of 14,400 seconds and applies
the following NatureBench defaults to `inner_agent`:

| `inner_agent` | NatureBench defaults |
|---|---|
| `claude-code` | `disallowed_tools=WebSearch,WebFetch` |
| `codex` | `web_search=disabled` |

These defaults can be overridden by passing the corresponding agent parameters
through `--ak`.

**`NatureBenchDockerEnvironment`:**

The environment extension only declares GPU support; it does not perform GPU scheduling.

## Harbor tasks

**Task structure:**

Each Harbor task contains the task-specific inputs, environments, evaluator, verifier, and license files:

```text
<task-id>/
├── task.toml                 # Harbor configuration
├── instruction.md            # NatureBench agent prompt
├── licenses/
├── environment/
│   ├── Dockerfile            # Agent execution environment
│   ├── docker-compose.yaml   # Main container and evaluation sidecar
│   ├── input/                # Read-only task description and data
│   └── sidecar/              # evaluation service
└── tests/
    ├── Dockerfile            # Separate verifier environment
    ├── test.sh
    ├── verifier.py
    └── context/
```

**Runtime components:**

| Component | Responsibility | Agent access |
|---|---|---|
| Main container | Runs the agent with read-only input at `/task/problem` and a writable `/workspace`. | Full access to its task input and workspace. |
| `naturebench-eval` sidecar | Runs the hidden task evaluator, measures agent solve time with evaluator runtime excluded, and tracks every attempt and the best score. | Provides the `/health`, `/evaluate`, `/best_score`, and `/time_remaining` HTTP endpoints. |
| Separate verifier | Reads the finalized best score and runs the NatureBench validity judge. | Starts after the agent phase and is not agent-accessible. |

**Compute requirements and healthcheck:**

- `cpu` tasks request no GPU.
- `gpu_low` tasks require exactly one visible RTX 3090 or RTX 4090.
- `gpu_high` tasks require exactly one visible A800 or A100.

For each GPU task, Compose requests one NVIDIA GPU for the main container. The
main-container healthcheck verifies that exactly one GPU is visible and that it
matches the task's GPU model requirements. The agent starts only after this
check succeeds; otherwise, environment setup fails.

**Outputs:**

| Path | Content |
|---|---|
| `/workspace` | Final agent workspace, including the solution and results. |
| `/logs/agent/trajectory.json` | Complete Harbor trajectory. |
| `/state/submissions.jsonl` | One record for every evaluation attempt. |
| `/state/best_score.json` | Finalized best attempt, best score, and agent solve-time information. |
| `/logs/verifier/reward.json` and `judge_verdict.json` | Harbor reward and full validity-judge result. |
| `/logs/verifier/summary.json` | Best attempt, best aggregate score, judge verdict, and effective aggregate score. |

For a valid scored run, the Harbor reward equals the best aggregate
improvement. A run with no score or an invalid judge verdict receives a
reward of `-1`.

## Run

### Install

Prerequisites are Python 3.12+, Docker, Harbor 0.20+, and the `huggingface_hub`
Python package. Then install the NatureBench extensions, build the required
images, and download the Harbor tasks:

```bash
cd NatureBench/harbor

python -m pip install -e ./extensions
bash scripts/build_images.sh
python scripts/download_tasks.py --output-dir ./tasks
```

Without a selector, the script installs all 90 tasks. To install only selected
tasks, add `--task-ids`:

```bash
python scripts/download_tasks.py \
  --output-dir ./tasks \
  --task-ids s43588-024-00689-2 s42256-024-00833-7
```

To install tasks by compute group, use `--compute`. `--compute` and `--task-ids`
are alternative selectors and cannot be used together. Multiple groups can be selected
in one command:

```bash
python scripts/download_tasks.py \
  --output-dir ./tasks \
  --compute cpu

python scripts/download_tasks.py \
  --output-dir ./tasks \
  --compute gpu_low gpu_high
```

The Harbor tasks on Hugging Face are distributed as compressed archives. The
download script automatically downloads the selected tasks and extracts them
into `tasks/`.

### Execute

Set the selected agent's credentials and the independent judge credentials.
The example below uses Claude Code; replace the agent and model as needed.

```bash
export ANTHROPIC_API_KEY=...
export ANTHROPIC_BASE_URL=...
export JUDGE_API_KEY=...
export JUDGE_BASE_URL=...
export JUDGE_MODEL=gpt-5.5

harbor run \
  -p ./tasks \
  -a naturebench_extensions.timed_agent:NatureBenchTimedAgent \
  -m <model-name> \
  --ak inner_agent=claude-code \
  --ak timeout=14400 \
  -e naturebench_extensions.docker_environment:NatureBenchDockerEnvironment \
  --ae ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --ae ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL" \
  -o outputs \
  -n 1
```

Alternatively, edit the agent and model settings in `run.yaml`, then run the
evaluation from the file:

```bash
harbor run \
  -c run.yaml \
  --ae ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --ae ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL" \
  -o outputs
```

### Harbor timeout display issue

When the NatureBench solve-time budget is exhausted, `NatureBenchTimedAgent`
ends the inner agent run and raises `AgentTimeoutError`. Harbor catches this
exception and writes the timeout field in its output using
`[agent].timeout_sec` from `task.toml`. This agent timeout is set
to 43,200 seconds to allow enough wall-clock time for both agent solving and
evaluator execution, whereas `--ak timeout` counts only agent solve time and
defaults to 14,400 seconds. Therefore, an output file reporting a 43,200-second
timeout does not mean that the agent spent 43,200 seconds solving the task; instead
it only indicates that the run reached the NatureBench solve-time budget.
