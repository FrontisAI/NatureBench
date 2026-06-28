# Running NatureBench with the Lumen agent

[Lumen](https://github.com/) is a terminal coding agent shipped as a single
static Go binary. It is wired into NatureBench through the standard
[`AgentAdapter`](../agent/adapter.py) interface (see
[custom-agents.md](custom-agents.md), Path B) — no changes to `solve.py`.

## How it works

| Piece | Where |
|---|---|
| Adapter | [`agent/lumen_adapter.py`](../agent/lumen_adapter.py) — registers as `lumen` |
| Registration | imported from [`agent/__init__.py`](../agent/__init__.py), so `solve.py`'s `import agent.cli_adapters` picks it up |
| Image | [`docker/Dockerfile.lumen`](../docker/Dockerfile.lumen) — `naturebench-base:v3` + the `lumen` binary |

The adapter:

- **Prompt** — reuses the built-in Claude task prompt verbatim, so the evaluation
  protocol (write to `OUTPUT_DIR`, submit to `$EVAL_SERVICE_URL/evaluate`) is
  identical to the built-in CLIs and the score stays comparable.
- **Launch** — `lumen run --mode bypass "<prompt>"`. Headless Lumen auto-approves
  tool calls and never blocks on a TTY prompt, so it runs to completion and exits.
- **Model / provider** — `lumen run` has no `--model` flag; the adapter writes a
  `lumen.toml` into `/workspace` at launch with the requested model and the
  `core` tool profile (no web tools, matching the built-ins' `--disallowedTools`).
  Defaults target DeepSeek (OpenAI-compatible). The provider key is forwarded
  from the host env (`DEEPSEEK_API_KEY`); override the endpoint with
  `DEEPSEEK_BASE_URL` to point at any OpenAI-compatible server (e.g. a local
  model).

## One-time setup

```bash
# 1. Cross-compile the linux/amd64 binary in your lumen checkout:
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="-s -w" \
    -o /path/to/NatureBench/docker/lumen ./cmd/lumen

# 2. Ensure the base image exists, then build the Lumen image:
bash scripts/ensure_naturebench_base.sh
docker build -t naturebench-lumen:v3 -f docker/Dockerfile.lumen docker
```

## Run

```bash
export DEEPSEEK_API_KEY=sk-...        # provider key (forwarded into the container)

python run_naturebench.py \
    --agent lumen --model deepseek-chat \
    --tasks cpu \
    --skip-build --base-image naturebench-lumen:v3 \
    --start-eval-services --eval-env-mapping eval_env_mapping.json
```

`--model` accepts any model valid for the configured provider (e.g.
`deepseek-chat`, `deepseek-reasoner`). Swap `--tasks cpu` for `gpu_low` /
`gpu_high` / `all` once a GPU host is available — note 87 of the 90 tasks
require CUDA, so a CPU-only host can only run the 3 `cpu` tasks.

## Verifying the integration without a full run

```bash
# adapter unit tests (registration, command shape, env forwarding):
python -m pytest agent/lumen_adapter_test.py -q

# confirm solve.py will accept --agent lumen:
python -c "import agent.cli_adapters; from agent.adapter import REGISTRY; \
print(REGISTRY.names())"
```
