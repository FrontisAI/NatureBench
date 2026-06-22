# Usage and Parameter Reference

This document covers the full set of run examples, the complete parameter reference, and output formats. For a minimal end-to-end command, see the Quick Start in the top-level [`README`](../README.md). For agent authentication, network proxy, and the evaluation service, see [`configuration.md`](configuration.md).

## Run Examples

### Prepare data only

```bash
python run_naturebench.py \
  --dataset-id FrontisAI/NatureBench \
  --tasks all \
  --download-only
```

### CPU Smoke Run

For a first run, start with `cpu` as a smoke test. If the evaluation service has not been started, `--start-eval-services` must be used together with `--eval-env-mapping`; if the service is already running, remove `--start-eval-services` and keep `--eval-env-mapping`.

```bash
python run_naturebench.py \
  --dataset-id FrontisAI/NatureBench \
  --tasks cpu \
  --agent claude \
  --model <model-name> \
  --out-dir ./results/cpu_smoke \
  --start-eval-services \
  --eval-env-mapping ./eval_env_mapping.json \
  --skip-build
```

### Codex Official Login State + Embedded Proxy

This is the recommended launch mode for Codex device-auth. Before running, complete `codex login --device-auth` and prepare `.clash-bundle/`, or specify a bundle with `--proxy-bundle`.

```bash
python run_naturebench.py \
  --dataset-id FrontisAI/NatureBench \
  --tasks gpu_low \
  --agent codex \
  --model <model-name> \
  --gpu-devices 0,1,2,3 \
  --max-workers 4 \
  --start-eval-services \
  --eval-env-mapping ./eval_env_mapping.json \
  --skip-build \
  --codex-auth-mode device-auth \
  --codex-auth-dir ~/.codex \
  --proxy-mode embedded \
  --proxy-bundle ./.clash-bundle
```

### GPU Batch Run

GPU tasks usually require a task set, a GPU list, and a parallelism setting. `--max-workers` is the number of task worker threads and may exceed the currently available number of GPU slots; workers that cannot acquire a GPU wait in the GPU allocator. In the normal GPU pool, each task exclusively occupies one GPU.

```bash
python run_naturebench.py \
  --dataset-id FrontisAI/NatureBench \
  --tasks gpu_low \
  --agent claude \
  --model <model-name> \
  --gpu-devices 0,1,2,3 \
  --max-workers 4 \
  --start-eval-services \
  --eval-env-mapping ./eval_env_mapping.json \
  --ensure-base-image \
  --skip-build
```

### Resume Runs

If some task agents exit before completing the task, use the harness resume mechanism.

Resume continues an existing agent session. It requires:

- the task directory to preserve the full previous evaluation output, plus the agent's session id and state directory;
- the running evaluation service to still hold that task's evaluation state — so do not restart the service before resuming.

Resume only selected tasks:

```bash
python run_naturebench.py \
  --skip-download \
  --data-dir ./data/naturebench_data \
  --tasks gpu_low \
  --agent codex \
  --model <model-name> \
  --out-dir ./results/codex_gpu_low \
  --start-eval-services \
  --eval-env-mapping ./eval_env_mapping.json \
  --codex-auth-mode device-auth \
  --proxy-mode embedded \
  --proxy-bundle ./.clash-bundle \
  --resume-tasks s41592-025-02886-x s42256-024-00892-w \
  --resume-only
```

Without `--resume-only`, the script resumes tasks listed in the resume list and tries to fresh-run other remaining tasks in the same task set. If those other tasks already have prior state and are not listed in `--resume-tasks` or `--force-fresh`, the pipeline errors out to avoid accidental overwrite.

You can also list tasks in a file:

```bash
python run_naturebench.py ... \
  --resume-task-file ./resume_tasks.txt \
  --resume-only
```

## Parameter Usage

`run_naturebench.py` is the recommended entry point. It downloads selected tasks and launches evaluation.

### Quick Start Defaults

The Quick Start command in the [`README`](../README.md) sets only the parameters you must choose; every other option uses its default. The defaults that shape that run are listed below.

<details>
<summary>Defaults used by the Quick Start command</summary>

| Parameter | Default | Effect |
|---|---|---|
| `--dataset-id` | `FrontisAI/NatureBench` | Download from the official Hugging Face dataset. |
| `--dataset-revision` | `None` | Latest commit on the HF default branch. |
| `--data-dir` | `./data/naturebench_data` | Download / read location. |
| `--skip-download` | off | Data is downloaded — this is what makes the Quick Start run "download, then evaluate". |
| `--mode` | `base` | Public benchmark protocol (not `reproduce`). |
| `--timeout` | `14400` (4 h) | Per-task agent solve budget. |
| `--setup-timeout` | `14400` (4 h) | Container setup-stage cap. |
| `--skip-build` | on | Overlay on the base image and parse `Dockerfile.v3` during setup; no per-task image build. |
| `--base-image` | `naturebench-base:v3` | Base image. |
| `--dockerfile-name` | `Dockerfile.v3` | Per-task Dockerfile. |
| `--skip-judge` | off | The post-hoc validity judge runs. |
| `--eval-log-dir` | `./eval_logs` | External evaluation service log directory. |
| `--proxy-mode` | per agent (`host` for Claude) | Claude passes the host proxy into containers. |
| `--proxy-http-port` / `--proxy-socks-port` | `7890` / `7891` | Used only by `embedded` / `sidecar`. |

Features that stay off unless you opt in: the cross-process GPU pool (`--gpu-pool-file`), busy-GPU avoidance (`--gpu-skip-busy-*`), the shared GPU slot pool (`--shared-gpu-*`), resume / force-fresh (`--resume-*`, `--force-fresh-*`), and Codex authentication (`--codex-auth-*`). The internal evaluation port (`--eval-port`) is unused because the Quick Start runs the external service via `--eval-env-mapping`.

</details>

### Configuration File

| Parameter | Default | Usage |
|---|---|---|
| `--config` | Automatically uses `./config.yaml` if it exists | Optional YAML config file. Explicit CLI arguments take precedence over config values. |

`config.example.yaml` contains two sections:

| Section | Used By | Purpose |
|---|---|---|
| `run:` | `run_naturebench.py` | Recommended entry-point configuration. |
| `solve:` | `solve.py --config config.yaml` | Used only when calling the low-level evaluation orchestrator directly. |

Usually you only need to edit `run:`. `run_naturebench.py` automatically calls `solve.py`. Maintain `solve:` only if you run `solve.py --config config.yaml` directly.

If you do not want the current directory's `config.yaml` to be read automatically, delete or rename it, or override its settings with explicit CLI arguments.

### Data And Task Selection

| Parameter | Default | Usage |
|---|---|---|
| `--tasks` | `all` | Task selection entry point. Use `all`, `cpu`, `gpu_high`, `gpu_low`, or a custom task-list file. |
| `--dataset-id` | `FrontisAI/NatureBench` | Hugging Face dataset id; usually unchanged. |
| `--dataset-revision` | `None` | Uses the latest version from the HF default branch at download time; usually unchanged. |
| `--data-dir` | `./data/naturebench_data` | Dataset download or local data directory. |
| `--skip-download` | off | Use when data already exists locally; pair with `--data-dir`. |
| `--download-only` | off | Download selected tasks only; does not start evaluation service or agent. |

### Output Directory And Batch

| Case | Final Output Directory | Notes |
|---|---|---|
| Pass `--out-dir ./results/my_run` | `./results/my_run/` | Recommended for formal runs and resume. |
| Omit `--out-dir`, pass `--batch-name my_run` | `./results/my_run/` | `--batch-name` only participates in naming when `--out-dir` is omitted. |
| Omit both | `./results/<agent>_<model>_<tasks>_<timestamp>/` | Automatic timestamped directory; not recommended for later resume. |

Each task's session, workspace, submissions, and results are written under `--out-dir/<case_id>/`. The evaluation service `batch_name` is the final output directory's last path component. For resumable formal runs, fix `--out-dir` or `--batch-name`.

When reusing the same `--out-dir`, tasks with prior state require an explicit choice between `--resume-tasks` and `--force-fresh`; this avoids accidental overwrites.

### Agent And Mode

| Parameter | Default | Usage |
|---|---|---|
| `--agent` | none | Required unless `--download-only` is used. Must be `claude`, `codex`, or `gemini`. |
| `--model` | none | Model name passed to the corresponding CLI. Required unless `--download-only` is used. |
| `--mode` | `base` | Public benchmark protocol uses `base`. `reproduce` additionally mounts paper PDF/Markdown for task calibration. |
| `--timeout` | `14400` | Per-task agent solve budget, in seconds. |
| `--setup-timeout` | `14400` | Container setup-stage cap, in seconds. Setup time does not count toward the agent solve budget. The default `--skip-build` path installs task dependencies during setup. |

### Docker And Task Environment

| Parameter | Default | Usage |
|---|---|---|
| `--skip-build` | on | Default path: do not build a separate image per task. Start from the base image and parse `environment/Dockerfile.v3` during container setup. |
| `--build-task-images` | off | Build a complete Docker image for each task. Slower, but task images can be reused later. `--setup-timeout`. |
| `--ensure-base-image` | off | Check and build `naturebench-base:v3` before running. |
| `--base-image` | `naturebench-base:v3` | Current release default base image. |
| `--dockerfile-name` | `Dockerfile.v3` | Current release default task Dockerfile. |

### Evaluation Service

| Parameter | Default | Usage |
|---|---|---|
| `--start-eval-services` | off | Start the external evaluation service. Use this for the first formal run; usually do not repeat it when the service is already running. |
| `--eval-env-mapping` | none | Task-to-port mapping for external evaluation service. Recommended for formal runs. |
| `--eval-port` | `8321` | Internal evaluation service port; for small debugging runs only. |
| `--eval-log-dir` | `./eval_logs` | External evaluation service log directory. |
| `--skip-judge` | off | Skip post-hoc validity judge. |

### GPU Scheduling

| Scenario | Parameters | Notes |
|---|---|---|
| CPU tasks | no GPU parameters | For `--tasks cpu`. |
| Normal exclusive GPU | `--gpu-devices 0,1,2,3 --max-workers 4` | Each GPU task exclusively occupies one GPU. |
| Cross-process normal GPU pool | add `--gpu-pool-file /tmp/naturebench_gpu_pool.json` | Multiple evaluation processes must share the same pool file to avoid racing for the same GPU. |
| Avoid externally busy GPUs | `--gpu-skip-busy-mb` / `--gpu-skip-busy-util` | Checks memory and utilization before acquiring a GPU; keep defaults on shared machines. |

```bash
--gpu-devices 0,1,2,3 \
--max-workers 4
```

`--max-workers` controls the number of active workers and may exceed the number of available GPUs/slots; workers wait when no GPU is available.

Shared GPU slot pool:

The shared GPU slot pool schedules tasks from a designated task-set onto multiple slots on a single GPU, so you can choose which tasks to co-locate based on their actual GPU-memory and compute footprint.

| Parameter | Required | Notes |
|---|---|---|
| `--shared-gpu-task-file` | yes | Lists tasks that use the shared slot pool. |
| `--shared-gpu-device` | yes | Physical GPU used as the shared slot pool. |
| `--shared-gpu-pool-file` | yes | Cross-process state file for shared slots. |
| `--shared-gpu-slots` | no, default `5` | Number of task containers allowed concurrently on the shared GPU; specify explicitly for formal runs. |

When normal and shared tasks are mixed in one `--tasks`, tasks listed in `--shared-gpu-task-file` use the shared pool, while other GPU tasks use the normal `--gpu-devices` exclusive pool:

```bash
--gpu-devices 0,1,2 \
--gpu-pool-file /tmp/naturebench_gpu_pool.json \
--shared-gpu-task-file ./task-set/shared_gpu_tasks.txt \
--shared-gpu-device 3 \
--shared-gpu-slots 5 \
--shared-gpu-pool-file /tmp/naturebench_shared_gpu_pool.json
```

If only shared-pool tasks are run, omit normal `--gpu-devices` and make `--tasks` and `--shared-gpu-task-file` point to the same list. The code allows `--shared-gpu-device` to also appear in normal `--gpu-devices`, but it warns because this double-books the physical GPU; unless you know the resource profile, keep the shared GPU out of the normal pool.

### Network Proxy Parameters

| Mode | Companion Parameters | Usage |
|---|---|---|
| `host` | none required | Pass host `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`, and lowercase variants into containers. The proxy address must be reachable from inside containers. |
| `embedded` | `--proxy-bundle` optional; defaults to `./.clash-bundle` | Start Clash/Mihomo inside each task container and inject container-local `127.0.0.1` proxy variables. |
| `sidecar` | `--proxy-container`, `--proxy-network` required | Use a user-started shared proxy container. |
| `none` | none | Do not inject proxy variables; containers use Docker default networking directly. |

- **Ports:** `--proxy-http-port` and `--proxy-socks-port` (used by `embedded` / `sidecar`) default to `7890` and `7891`.
- **Per-agent defaults:** Codex defaults to `embedded`; Claude and Gemini default to `host`.
- **Override:** an explicit `--proxy-mode` overrides these defaults.

For `embedded`, provide your own Clash/Mihomo bundle (not included in this repository); `--proxy-bundle` defaults to `./.clash-bundle`:

```text
.clash-bundle/
├── clash                  # executable; can also be a compatible mihomo/clash binary
└── config/
    ├── config.yaml
    └── Country.mmdb       # required if referenced by config.yaml
```

For `sidecar`, start your own proxy container on a shared Docker network and point the pipeline at it:

```bash
docker network create naturebench-net
# Start your clash/mihomo container, exposing 7890/7891 inside the container.

python run_naturebench.py ... \
  --proxy-mode sidecar \
  --proxy-container naturebench-clash \
  --proxy-network naturebench-net
```

### Resume And Force-fresh

| Mode | Use Case | Typical Parameters |
|---|---|---|
| Normal fresh run | First run in an `--out-dir`, or no prior state exists for the task. | no `--resume-*` / `--force-fresh` |
| resume | Continue an existing agent session, preserving task context and evaluator timer history. | `--resume-tasks ...` or `--resume-task-file ...` |
| force-fresh | Start from scratch and archive old state. | `--force-fresh ...` or `--force-fresh-task-file ...` |

| Rule | Behavior |
|---|---|
| Default fresh run | Tasks with no prior state start a new agent session. |
| Fresh meets prior state | If any task already has `result.json`, `submissions.jsonl`, agent session/state, or logs, `solve.py` errors out before any task starts and stops the whole run. |
| Resume eligibility | Requires complete previous task output plus the corresponding agent session and state files. |
| `--resume-only` | Runs only tasks in the resume list; without it, the task set's other tasks are processed too. |
| force-fresh scope | Applies only to tasks that are both in current `--tasks` and listed in `--force-fresh`; there is no `--force-fresh-only`. |
| resume + force-fresh | Can be combined in one command, but not for the same task. Other tasks run fresh. |

### More parameters

```bash
python run_naturebench.py --help
python solve.py --help
```

## Outputs

Each task's result is written under `--out-dir/<case_id>/`:

| File Or Directory | Description |
|---|---|
| `result.json` | Per-task execution metadata such as status, return code, duration, session id, and resume history. |
| `submissions.jsonl` | Every agent `/evaluate` submission, including attempt, raw scores, per-instance improvement, and aggregate improvement. Failed submissions are recorded as well. |
| `judge_verdict.json` | Post-hoc validity judge output, if judge is enabled. |
| `workspace/` | Final agent workspace snapshot. |

Batch-level summary is written to `--out-dir/run_summary.json`. It includes `total_tasks`, `successes` (tasks whose return code is success), `scored_tasks` (tasks whose submissions produced a score), `average_best_aggregate_improvement` (averaged only over scored tasks), total duration, and for each task: `status`, `duration`, `best_attempt`, `best_aggregate_improvement`, `best_raw_scores`, `total_attempts`, and judge results.
