<div align="center">

# NatureBench

**Can coding agents match the published SOTA of Nature-family papers?**

[![arXiv](https://img.shields.io/badge/arXiv-b31b1b?style=for-the-badge&logo=arxiv&logoColor=ffffff)](https://arxiv.org/abs/2606.24530) &nbsp; [![Hugging Face Dataset](https://img.shields.io/badge/HUGGINGFACE-fcd022?style=for-the-badge&logo=huggingface&logoColor=000)](https://huggingface.co/datasets/FrontisAI/NatureBench) &nbsp; [![Leaderboard](https://img.shields.io/badge/Leaderboard-steelblue?style=for-the-badge&logo=googlechrome&logoColor=ffffff)](https://frontisai.github.io/NatureBench/)

[📖 Overview](#overview) • [🔧 Installation](#installation) • [🚀 Quick Start](#quick-start) • [🌱 NatureGym](#naturegym) • [📚 Documentation](#documentation) • [⚖️ License](#license) • [🎈 Citation](#citation)

</div>

## 📖Overview

NatureBench is a cross-discipline benchmark of **90 tasks** distilled from peer-reviewed Nature-family publications, spanning **6 scientific domains**, designed to evaluate whether AI coding agents can move beyond reproduction toward discovery. Each task asks an agent to solve a real scientific machine-learning problem and is scored against the source paper's reported state of the art.

NatureBench is built on **NatureGym**, an automated pipeline that converts a published paper into a containerized task package comprising a task brief, the paper's dataset, a held-out test set with hidden ground truth, and an automated evaluator.

<p align="center">
  <img src="assets/overview.png" width="880" alt="NatureBench overview">
</p>

## 📊Results

The strongest configuration reaches a 17.8% Surpass-SOTA rate, and success remains uneven across the six scientific domains NatureBench spans.

<p align="center">
  <img src="assets/main_results.png" width="840" alt="NatureBench scientific domains and Surpass-SOTA rates across agent-model configurations">
</p>

## 🔧Installation

```bash
git clone https://github.com/FrontisAI/NatureBench.git
cd NatureBench

conda env create -f conda_env.yml
conda env create -f conda_env_eval.yml
conda activate naturebench
```

This creates two environments: `naturebench` (the main orchestration environment that runs `run_naturebench.py`, agent adapters, Docker scheduling, and result aggregation) and `naturebench-eval` (the evaluation service environment that runs scoring logic).

The base Docker image is built automatically on the first run via `--ensure-base-image` (used in the Quick Start below). To build it manually:

```bash
bash scripts/ensure_naturebench_base.sh
```

## 🚀Quick Start

Set credentials for your agent. Claude Code is shown here; for Codex, Gemini CLI, the post-hoc judge, and network proxy, see [`docs/configuration.md`](docs/configuration.md).

```bash
export ANTHROPIC_API_KEY=...
export ANTHROPIC_BASE_URL=...
```

Run end-to-end. This single command downloads the dataset, builds the base image if needed, starts the evaluation service, and evaluates:

```bash
python run_naturebench.py \
  --tasks gpu_low \
  --agent claude \
  --model <model-name> \
  --out-dir ./results/claude_<model-name>_gpu_low \
  --gpu-devices 0,1,2,3 \
  --max-workers 4 \
  --start-eval-services \
  --eval-env-mapping ./eval_env_mapping.json \
  --ensure-base-image
```

This lists only the parameters you set explicitly; options with sensible defaults are omitted (see [Quick Start defaults](docs/usage.md#quick-start-defaults) for the full list and their values). Adjust `--gpu-devices` / `--max-workers` to your hardware, or use `--tasks cpu` (without the GPU flags) for a GPU-free run. 
In our experiments each task ran on a single GPU matched to its compute tier: `gpu_low` tasks on one NVIDIA RTX 3090/4090 (24 GB) and `gpu_high` tasks on one NVIDIA A800 (80 GB, A100-class), with the 3 `cpu` tasks using none. The complete parameter reference is in [`docs/usage.md`](docs/usage.md).

## 🌱NatureGym

The task packages are built by **NatureGym**, an automated, Skills-based pipeline that turns a published Nature-family paper into a containerized, runnable task. It filters papers, acquires and verifies the data, and assembles the task package (brief, data, evaluator, environment, metadata), while an information firewall removes the source method so that agents must *discover* solutions rather than reproduce them.

The pipeline runs as a chain of Claude Code skills driven by batch scripts, all under [`naturegym/`](naturegym/). See [`naturegym/README.md`](naturegym/README.md) for the stage-by-stage flow, the construction skills, and how to run them.

## 📦Repository Contents

- `run_naturebench.py` — one-command entry point: download data and launch evaluation
- `solve.py` — main evaluation orchestrator
- `eval_service.py` — host-side evaluation service
- `judge.py` — post-hoc validity judge
- `agent/` — adapters for Claude Code / Codex CLI / Gemini CLI
- `evaluator/` — evaluator interface
- `docker/Dockerfile.base` — NatureBench base Docker image
- `scripts/` — helper scripts
  - `ensure_naturebench_base.sh` — build the NatureBench base image if it is missing
  - `start_eval_services.sh` — start evaluation service from the mapping file
- `task-set/` — task lists grouped by resource demand
- `docs/` — detailed configuration, usage, and task-package reference
- `naturegym/` — NatureGym construction pipeline: skills + batch drivers that build task packages from papers
- `conda_env.yml` — main orchestration environment
- `conda_env_eval.yml` — evaluation service environment
- `eval_env_mapping.json` — task-to-evaluation-service port mapping
- `config.example.yaml` — example configuration file
- `LICENSE`, `NOTICE` — MIT license for original work; `NOTICE` defines the scope

## 📚Documentation

| Document | Contents |
|---|---|
| [`docs/configuration.md`](docs/configuration.md) | Agent authentication (Claude Code / Codex CLI / Gemini CLI), the post-hoc judge, network proxy, and the evaluation service. |
| [`docs/usage.md`](docs/usage.md) | More run examples (CPU, GPU batch, Codex login, resume), the complete parameter reference, and output formats. |
| [`docs/task-packages.md`](docs/task-packages.md) | Task package structure and the resource-grouped task lists. |

## ⚖️License

The top-level [`LICENSE`](LICENSE) is the MIT License and applies only to original NatureBench contributions; see [`NOTICE`](NOTICE) for the exact scope. Third-party data bundled in each task package is governed by the notices in that task's `tasks/<case_id>/licenses/` directory.

## 🎈Citation

If you use NatureBench in your research, please cite our work:

```bibtex
@misc{wang2026naturebench,
  title         = {NatureBench: Can Coding Agents Match the Published SOTA of Nature-Family Papers?},
  author        = {Yuru Wang and Lejun Cheng and Yuxin Zuo and Sihang Zeng and Bingxiang He and Che Jiang and Junlin Yang and Yuchong Wang and Kaikai Zhao and Weifeng Huang and Kai Tian and Zhenzhao Yuan and Jincheng Zhong and Weizhi Wang and Ning Ding and Bowen Zhou and Kaiyan Zhang},
  year          = {2026},
  eprint        = {2606.24530},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  url           = {https://arxiv.org/abs/2606.24530}
}
```
