"""NatureBench adapter for the Lumen coding agent (https://github.com/…/lumen).

Lumen is a single static Go binary run non-interactively as ``lumen run
<prompt>``. It runs the agent loop to completion and exits, auto-approving tool
calls in headless mode — which matches NatureBench's container execution model
(``docker exec`` a one-shot command, no TTY, the agent submits to the eval
service over HTTP and then returns).

Design notes
------------
* **Prompt** — reuses the built-in Claude task prompt verbatim. The NatureBench
  evaluation protocol (DATA_DIR / OUTPUT_DIR / submit to ``$EVAL_SERVICE_URL``)
  is model-agnostic plain-text instructions, so handing Lumen the same prompt
  keeps its score comparable with the built-in CLIs.
* **Model / provider** — ``lumen run`` has no ``--model`` flag; model and
  provider come from ``lumen.toml`` (found in the working dir) plus an API key
  from the environment. ``build_command`` therefore writes a ``lumen.toml`` into
  ``/workspace`` (Lumen's cwd, which it searches first) with the requested model
  before launching. Defaults target DeepSeek (OpenAI-compatible); override the
  endpoint with ``DEEPSEEK_BASE_URL`` in the host env.
* **No web** — the config pins the ``core`` tool profile, so Lumen is not handed
  its web/search tools (NatureBench disallows web access for the built-ins too).
* **Auto-approve** — ``--mode bypass`` plus Lumen's headless auto-approve means
  no interactive permission prompt can stall the run.
"""
from __future__ import annotations

import os
from typing import List

from .adapter import REGISTRY, AgentAdapter, AgentRunContext
from .claude import ClaudeAgent

# Resume notice mirrors the built-in adapters: Lumen's `run` is stateless across
# container restarts, but /workspace and any prior /evaluate submissions are
# preserved on disk, so "continue from the workspace" is the right instruction.
_RESUME_PROMPT = (
    "[RESUME NOTICE] You were previously interrupted on this task. "
    "The /workspace contents and any prior /evaluate submissions are preserved. "
    "Continue from where you left off. "
    "**Use the full remaining time budget**: keep iterating, profiling, and "
    "refining until `/time_remaining` is close to zero. Do **not** exit early "
    "just because you have a working baseline. Check `/time_remaining` first."
)

# Default provider endpoint (DeepSeek is OpenAI-compatible). Overridable per-run
# via the DEEPSEEK_BASE_URL host env var so the same adapter can point Lumen at a
# local OpenAI-compatible server without code changes.
_DEFAULT_BASE_URL = "https://api.deepseek.com/v1"


class LumenAdapter(AgentAdapter):
    name = "lumen"

    def system_prompt(self, ctx: AgentRunContext) -> str:
        if ctx.is_resume:
            return _RESUME_PROMPT
        return ClaudeAgent(model_name=ctx.model, mode=ctx.mode).build_system_prompt({
            "task_name": ctx.task_name,
            "batch_name": ctx.batch_name,
            "eval_service_url": ctx.eval_service_url,
            "eval_output_dir": ctx.eval_output_dir,
            "time_limit_minutes": ctx.time_limit_minutes,
        })

    def build_command(self, ctx: AgentRunContext) -> List[str]:
        base_url = os.environ.get("DEEPSEEK_BASE_URL") or _DEFAULT_BASE_URL
        # Lumen finds ./lumen.toml in its cwd (/workspace) first. Write it there
        # with the requested model, then exec the agent. The prompt is passed as
        # the positional "$1" so the (large, multi-line) system prompt never has
        # to be escaped into the script body — solve.py shlex-quotes each argv
        # element, so "$1" resolves to exactly ctx.system_prompt.
        config = (
            'default_model = "deepseek"\n'
            "\n"
            "[tools]\n"
            'profile = "core"\n'
            "\n"
            "[[providers]]\n"
            'name = "deepseek"\n'
            'kind = "openai"\n'
            f'base_url = "{base_url}"\n'
            f'model = "{ctx.model}"\n'
            'api_key_env = "DEEPSEEK_API_KEY"\n'
        )
        script = (
            "set -e\n"
            "mkdir -p /workspace\n"
            "cat > /workspace/lumen.toml <<'LUMEN_TOML_EOF'\n"
            f"{config}"
            "LUMEN_TOML_EOF\n"
            'exec lumen run --mode bypass "$1"\n'
        )
        return ["bash", "-lc", script, "lumen", ctx.system_prompt]

    def extra_env(self, ctx: AgentRunContext) -> List[str]:
        # solve.py forwards only the Anthropic/OpenAI/Gemini keys, so the Lumen
        # adapter forwards its own provider key from the host environment.
        env: List[str] = []
        for key in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"):
            val = os.environ.get(key)
            if val:
                env.extend(["-e", f"{key}={val}"])
        return env


REGISTRY.register(LumenAdapter())
