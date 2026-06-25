# Custom Agents

NatureBench is harness-agnostic at the protocol level. Every task runs in a
container with read-only data and a host-side **evaluation service**; the agent
writes outputs and submits them over HTTP for a SOTA-normalized score. The
built-in Claude Code, Codex, and Gemini CLIs are wired in through the same
adapter interface that a custom agent can use.

There are two ways to plug in a custom agent. Pick based on whether you want
NatureBench to orchestrate the run for you.

| Path | You provide | NatureBench provides |
|---|---|---|
| **A. Protocol-only** | Your agent + your own runner | The task packages and the evaluation protocol |
| **B. Adapter** | An `AgentAdapter` subclass | Container orchestration, evaluation service, post-hoc judge |

---

## The evaluation protocol

This section documents how to use the evaluation service that NatureBench
provides; a custom agent must adapt to this interface to obtain a comparable
score.

Inside the task container the agent is given:

- `DATA_DIR=/task/problem/data` — read-only inputs (one sub-folder per instance).
- `OUTPUT_DIR=/workspace/output` — where outputs are written, one sub-folder
  per instance.
- `EVAL_SERVICE_URL` — base URL of the host-side eval service.

To get a score, the agent submits its output directory:

```bash
curl -s -X POST "$EVAL_SERVICE_URL/evaluate" \
  -H "Content-Type: application/json" \
  -d '{"task_name": "<task>", "batch_name": "<batch>", "output_dir": "/workspace/output"}'
```

The response includes `aggregate_improvement` (the SOTA-normalized score)
and `best_aggregate_improvement` (the highest score across all attempts).
The agent may evaluate many times; the **best** score across all
attempts is the final task score. Companion endpoints: `GET /health`,
`GET /best_score`, `GET /time_remaining`.

> The agent is responsible for *calling* `/evaluate` to get a score; NatureBench is responsible
> for *defining* the evaluation protocol above. The built-in CLIs receive these
> instructions inside their system prompt — if you reuse the built-in prompt
> builders, your agent gets them too.

---

## Path A — protocol-only

1. Download the task packages with the official script:

   ```bash
   python run_naturebench.py --dataset-id FrontisAI/NatureBench --tasks all --download-only
   ```

2. Run your own runner against the downloaded task packages. The orchestration
   is up to you, but to keep scores comparable with the built-in agents we
   recommend reusing — or at least referencing — NatureBench's own evaluation
   service and evaluation environment:

   - **Evaluation service** — reuse `eval_service.py` (started via
     [`scripts/start_eval_services.sh`](../scripts/start_eval_services.sh), see
     [`docs/configuration.md`](configuration.md)) so scoring, timing, and
     best-score tracking match the official protocol. Your agent then submits to
     `/evaluate` exactly as described in
     [The evaluation protocol](#the-evaluation-protocol).
   - **Evaluation environment** — run your agent inside the NatureBench Docker
     setup (`naturebench-base:v3` plus each task's `environment/Dockerfile.v3`)
     rather than an arbitrary local environment, so running environment matches the reported runs.

---

## Path B — write an adapter

An adapter tells `solve.py` how to launch your agent inside the standard task
container and (optionally) where its solve/iteration history lives for the
post-hoc judge. The interface lives in
[`agent/adapter.py`](../agent/adapter.py); the built-in CLIs in
[`agent/cli_adapters.py`](../agent/cli_adapters.py) are worked examples.

A minimal adapter only implements `system_prompt` and `build_command`:

```python
# agent/myagent_adapter.py
from typing import List
from agent.adapter import REGISTRY, AgentAdapter, AgentRunContext
from agent.claude import ClaudeAgent  # reuse the built-in task prompt, optional


class MyAgentAdapter(AgentAdapter):
    name = "myagent"            # the value passed to --agent

    def system_prompt(self, ctx: AgentRunContext) -> str:
        # Reuse the standard task prompt (includes the eval protocol), or build
        # your own (it must write run.py / output and submit to $EVAL_SERVICE_URL/evaluate).
        # ctx carries task_name, eval_service_url, eval_output_dir, etc.
        return ClaudeAgent(model_name=ctx.model, mode=ctx.mode).build_system_prompt({
            "task_name": ctx.task_name,
            "batch_name": ctx.batch_name,
            "eval_service_url": ctx.eval_service_url,
            "eval_output_dir": ctx.eval_output_dir,
            "time_limit_minutes": ctx.time_limit_minutes,
        })

    def build_command(self, ctx: AgentRunContext) -> List[str]:
        # The argv run inside the container; any executable form works
        # (a binary, `python -m ...`, a shell script, ...).
        # If your agent program is not already in the image, install it at runtime
        # here (see "Container image" below).
        return ["my-agent", "--model", ctx.model, "--prompt", ctx.system_prompt]


REGISTRY.register(MyAgentAdapter())
```

Optional hooks (all default to a no-op, so a minimal agent needs none):

- `docker_mounts(ctx)` / `extra_env(ctx)` — add extra `-v src:dst` mounts or
  `-e KEY=VALUE` variables to `docker run`. Use these when your agent needs a
  host path inside the container or an environment variable beyond the
  Anthropic/OpenAI/Gemini keys solve.py already forwards.
  `/task/problem` (read-only) and `/workspace` are mounted for every agent
  regardless.
- `transcript_path(task_out_dir)` / `transcript_excerptor()` — expose your
  agent's solve/iteration history to the post-hoc judge (see "Judge history"
  below).

### Selecting your agent

The registry is populated by importing the adapter module. Import it once before
`solve.py` dispatches (add an import line to `agent/__init__.py`), then select it:

```bash
python run_naturebench.py --agent myagent --model <model> --tasks cpu
```

An unknown `--agent` is rejected with the list of registered agents.

### Container image

The built-in CLIs are baked into the NatureBench base image. If your agent
program (binary, Python package, or script) is not already in the image, make
it available one of two ways:

- **Runtime install** — install it inside `build_command` (e.g.
  `["bash", "-lc", "pip install my-agent && my-agent ..."]`).
- **Extend the image** — build a derived image with your agent installed, then
  use it one of two ways: run it directly with `--skip-build --base-image
  <your-image>`, or tag it as the base name the task Dockerfiles build `FROM` so
  that per-task images are built on top of it.

### Judge history

After a run, the post-hoc validity judge reviews the agent's workspace code and,
when available, its solve/iteration history. Two hooks control this:

- `transcript_path(task_out_dir)` tells the judge where your agent's
  solve/iteration history log is. The built-in adapters return
  their internal session file or streamed stdout log. Returning `None` (the
  default) means the judge reviews only the final workspace code snapshot.
- `transcript_excerptor()` lets you supply a parser for your history-log format.
  The default (`None`) uses the built-in excerptor, whose format sniffing
  recognizes only the Claude/Codex/Gemini CLI logs and silently skips records it
  cannot parse. So if your agent writes a custom-format history log, return both
  a `transcript_path` and a `transcript_excerptor` to put its solve/iteration
  history in front of the judge; otherwise it is judged on code alone.

