"""Canonical in-container command builders for the built-in CLI agents.

These functions construct the exact argv that ``solve.py`` runs inside the
task container for the Claude Code, Codex, and Gemini CLIs. They live in a
neutral module (rather than inside ``solve.py``) so that the agent adapter
layer and ``solve.py`` share a single source of truth — the value passed to
``docker_cmd.extend(agent_cmd)`` is produced here and nowhere else.

The function bodies are pure (args in, ``list[str]`` out) and must stay
behaviour-preserving: any change here changes what every harness actually runs.
"""
from __future__ import annotations

from typing import List, Optional

# Dedicated HOME for Codex so its auth lookup is explicit (mounted ~/.codex).
_CODEX_HOME = "/tmp/codex-home"


def build_claude_cmd(
    system_prompt: str,
    model: str,
    *,
    session_id: Optional[str] = None,
    resume_session: bool = False,
) -> List[str]:
    """Build the Claude Code CLI command to run inside the container.

    When session_id is provided:
      - resume_session=False  → new session pinned to that UUID via --session-id.
      - resume_session=True   → continue prior session via --resume <uuid>.

    Without session_id this starts a fresh Claude Code session.
    """
    cmd: List[str] = ["claude"]
    if session_id:
        if resume_session:
            cmd.extend(["--resume", session_id])
        else:
            cmd.extend(["--session-id", session_id])
    cmd.extend([
        "-p", system_prompt,
        "--model", model,
        "--allowedTools", "Task,TaskOutput,Bash,Glob,Grep,ExitPlanMode,Read,Edit,Write,NotebookEdit,TodoWrite,KillShell,AskUserQuestion,Skill,EnterPlanMode,MCPSearch",
        "--disallowedTools", "WebSearch,WebFetch",
        "--permission-mode", "dontAsk",
        "--output-format", "stream-json",
        "--verbose",
    ])
    return cmd


def build_gemini_cmd(
    system_prompt: str,
    model: str,
    *,
    session_id: Optional[str] = None,
    resume_session: bool = False,
) -> List[str]:
    """Build the Gemini CLI command to run inside the container.

    Uses --output-format stream-json so the CLI prints structured JSONL events
    (init / message / result) to stdout. Without this flag the CLI defaults to
    a TTY/interactive mode that (a) produces no parsable log and (b) in the
    container uses native Gemini streaming.

    When session_id is provided:
      - resume_session=False  -> new session pinned to that UUID via --session-id.
      - resume_session=True   -> continue prior session via --resume <uuid>.
    """
    cmd: List[str] = ["gemini"]
    # Gemini CLI v1+ only accepts --resume <uuid|index|"latest">. There is no
    # --session-id flag, so fresh runs must not pin a UUID; the CLI generates
    # one and emits it in the stream-json "init" event.
    if session_id and resume_session:
        cmd.extend(["--resume", session_id])
    cmd.extend([
        "-p", system_prompt,
        "--model", model,
        "--yolo",
        "--policy", "/etc/naturebench/no-web.toml",
        "--output-format", "stream-json",
    ])
    return cmd


def build_codex_cmd(
    system_prompt: str,
    model: str,
    *,
    resume_session_id: Optional[str] = None,
    use_api_key: bool = False,
    api_base_url: Optional[str] = None,
) -> List[str]:
    """Build the Codex CLI command.

    Two auth-mode branches:

    * ``use_api_key=False`` (device-auth): rely on the
      mounted ``~/.codex`` login state. No provider override needed.

    * ``use_api_key=True``: use ``OPENAI_API_KEY``. If ``OPENAI_BASE_URL`` is
      set, register it as an OpenAI-compatible custom provider.
    """
    head: List[str] = ["codex", "exec"]
    if resume_session_id:
        head.append("resume")
        head.append(resume_session_id)

    cmd: List[str] = [*head]
    # `-C / --cd <DIR>` is only on `codex exec` (fresh); `codex exec resume`
    # rejects it. The container WORKDIR is already /workspace, so omitting
    # the flag on the resume path lands in the same cwd.
    if not resume_session_id:
        cmd.extend(["-C", "/workspace"])
    cmd.extend([
        "--skip-git-repo-check",
        "--yolo",
        "--json",
        "-c", "web_search=disabled",
    ])
    if use_api_key and api_base_url:
        base_url = api_base_url
        cmd.extend([
            "-c", 'model_provider="openai_compatible"',
            "-c", 'model_providers.openai_compatible.name="OpenAI Compatible"',
            "-c", f'model_providers.openai_compatible.base_url="{base_url}"',
            "-c", 'model_providers.openai_compatible.env_key="OPENAI_API_KEY"',
            "-c", 'model_providers.openai_compatible.wire_api="responses"',
        ])
    cmd.extend([
        "-m", model,
        system_prompt,
    ])
    return cmd


def codex_exec_cmd(base_cmd: List[str]) -> List[str]:
    """Run Codex with a dedicated HOME so auth lookup is explicit."""
    return ["env", f"HOME={_CODEX_HOME}", *base_cmd]


# ---------------------------------------------------------------------------
# Resume prompts (re-injected on a continuation run, since the CLIs re-read the
# system prompt fresh on resume).
# ---------------------------------------------------------------------------

# Claude resume prompt: minimal notice (claude does not need Session Rules,
# and does not need extra time-budget reminders — the time-budget bullet is
# already in CLAUDE_BASE_PROMPT and claude tends to use the full time anyway).
RESUME_PROMPT_CLAUDE = (
    "[RESUME NOTICE] You were previously interrupted on this task. "
    "The /workspace contents and any prior /evaluate submissions are preserved. "
    "Continue from where you left off. "
    "Check `/time_remaining` first before deciding what to do next."
)

# Codex resume prompt: re-inject the Session Rules block (the in-container codex
# CLI re-reads the system prompt fresh on resume) PLUS a time-budget reminder
# (codex tends to exit early; this counters that on resume runs).
RESUME_PROMPT_CODEX = (
    "# Session Rules\n"
    "You are running in non-interactive mode: your reply may include narration "
    "text, but it must contain at least one tool call. A reply that ends with "
    "text only (with no tool call after it) closes the session — even if the "
    "text says you'll continue. To plan or pivot, embed it in a tool call "
    "(e.g. `bash -lc 'echo \"switching to LightGBM\" >> /workspace/plan.log'`) "
    "and chain the next concrete action in the same call. Keep iterating until "
    "/time_remaining is near zero unless you are clearly above SOTA and have plateaued.\n\n"
    "[RESUME NOTICE] You were previously interrupted on this task. "
    "The /workspace contents and any prior /evaluate submissions are preserved. "
    "Continue from where you left off. "
    "**Use the full remaining time budget**: keep iterating, profiling, and refining until "
    "`/time_remaining` is close to zero. Do **not** exit early just because you have a "
    "working baseline or a 'reasonable' score. Only consider stopping early if your "
    "`best_aggregate_improvement` is clearly above 0 (above SOTA) AND further attempts have "
    "plateaued for several consecutive evaluations. "
    "Check `/time_remaining` first before deciding what to do next."
)

# Gemini resume prompt: Gemini CLI re-reads the system prompt fresh on resume,
# so we inject a time-budget reminder similar to codex.
RESUME_PROMPT_GEMINI = (
    "[RESUME NOTICE] You were previously interrupted on this task. "
    "The /workspace contents and any prior /evaluate submissions are preserved. "
    "Continue from where you left off. "
    "**Use the full remaining time budget**: keep iterating, profiling, and refining until "
    "`/time_remaining` is close to zero. Do **not** exit early just because you have a "
    "working baseline or a 'reasonable' score. Only consider stopping early if your "
    "`best_aggregate_improvement` is clearly above 0 (above SOTA) AND further attempts have "
    "plateaued for several consecutive evaluations. "
    "Check `/time_remaining` first before deciding what to do next."
)
