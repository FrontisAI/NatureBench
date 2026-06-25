"""Built-in adapters for the Claude Code, Codex, and Gemini CLIs.

Each adapter wraps the existing prompt builders (the ``*Agent`` classes) and the
canonical command builders (``agent.cli_commands``), plus the agent-specific
session-log location used by the post-hoc judge. Behaviour must stay identical
to the pre-adapter dispatch in ``solve.py``; the equivalence tests pin this.

Importing this module registers the three built-in adapters with the global
``REGISTRY``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .adapter import REGISTRY, AgentAdapter, AgentRunContext
from . import cli_commands as cc
from .claude import ClaudeAgent
from .codex import CodexAgent
from .gemini import GeminiAgent


def _task_info(ctx: AgentRunContext) -> Dict[str, Any]:
    """Reconstruct the prompt-template fields the *Agent classes expect."""
    return {
        "task_name": ctx.task_name,
        "batch_name": ctx.batch_name,
        "eval_service_url": ctx.eval_service_url,
        "eval_output_dir": ctx.eval_output_dir,
        "time_limit_minutes": ctx.time_limit_minutes,
    }


def _newest(paths: List[Path]) -> Optional[Path]:
    existing = [p for p in paths if p.is_file()]
    if not existing:
        return None
    try:
        return max(existing, key=lambda p: p.stat().st_mtime)
    except OSError:
        return existing[0]


class ClaudeAdapter(AgentAdapter):
    name = "claude"

    def system_prompt(self, ctx: AgentRunContext) -> str:
        if ctx.is_resume:
            return cc.RESUME_PROMPT_CLAUDE
        return ClaudeAgent(model_name=ctx.model, mode=ctx.mode).build_system_prompt(_task_info(ctx))

    def build_command(self, ctx: AgentRunContext) -> List[str]:
        return cc.build_claude_cmd(
            ctx.system_prompt, ctx.model,
            session_id=ctx.session_id,
            resume_session=ctx.is_resume,
        )

    def transcript_path(self, task_out_dir: Path) -> Optional[Path]:
        # Internal session jsonl is the most complete record; fall back to the
        # streamed stdout log written by solve.py.
        proj_dir = task_out_dir / ".claude_state" / "projects"
        if proj_dir.is_dir():
            cands = list(proj_dir.rglob("*.jsonl"))
            sid_file = task_out_dir / "claude_session_id.txt"
            if sid_file.exists():
                sid = sid_file.read_text(encoding="utf-8").strip()
                for c in cands:
                    if c.stem == sid:
                        return c
            newest = _newest(cands)
            if newest is not None:
                return newest
        stream = task_out_dir / "claude.jsonl"
        return stream if stream.exists() else None


class CodexAdapter(AgentAdapter):
    name = "codex"

    def system_prompt(self, ctx: AgentRunContext) -> str:
        if ctx.is_resume:
            return cc.RESUME_PROMPT_CODEX
        return CodexAgent(model_name=ctx.model, mode=ctx.mode).build_system_prompt(_task_info(ctx))

    def build_command(self, ctx: AgentRunContext) -> List[str]:
        cmd = cc.build_codex_cmd(
            ctx.system_prompt, ctx.model,
            resume_session_id=ctx.codex_resume_sid,
            use_api_key=ctx.codex_use_api_key,
            api_base_url=ctx.codex_api_base_url,
        )
        if ctx.codex_state_active:
            cmd = cc.codex_exec_cmd(cmd)
        return cmd

    def transcript_path(self, task_out_dir: Path) -> Optional[Path]:
        sess_dir = task_out_dir / ".codex_state" / "sessions"
        if sess_dir.is_dir():
            cands = list(sess_dir.rglob("rollout-*.jsonl"))
            sid_file = task_out_dir / "codex_session_id.txt"
            if sid_file.exists():
                sid = sid_file.read_text(encoding="utf-8").strip()
                for c in cands:
                    if sid in c.name:
                        return c
            newest = _newest(cands)
            if newest is not None:
                return newest
        stream = task_out_dir / "codex.jsonl"
        return stream if stream.exists() else None


class GeminiAdapter(AgentAdapter):
    name = "gemini"

    def system_prompt(self, ctx: AgentRunContext) -> str:
        if ctx.is_resume:
            return cc.RESUME_PROMPT_GEMINI
        return GeminiAgent(model_name=ctx.model, mode=ctx.mode).build_system_prompt(_task_info(ctx))

    def build_command(self, ctx: AgentRunContext) -> List[str]:
        return cc.build_gemini_cmd(
            ctx.system_prompt, ctx.model,
            session_id=ctx.session_id,
            resume_session=ctx.is_resume,
        )

    def transcript_path(self, task_out_dir: Path) -> Optional[Path]:
        tmp_dir = task_out_dir / ".gemini_state" / "tmp"
        if tmp_dir.is_dir():
            cands: List[Path] = []
            for pat in ("*/chats/*.json", "*/chats/*.jsonl"):
                cands.extend(tmp_dir.glob(pat))
            sid_file = task_out_dir / "gemini_session_id.txt"
            if sid_file.exists():
                sid = sid_file.read_text(encoding="utf-8").strip()
                short = sid[:8]
                for c in cands:
                    if c.stem == sid or sid in c.name or short in c.name:
                        return c
            newest = _newest(cands)
            if newest is not None:
                return newest
        stream = task_out_dir / "gemini.jsonl"
        return stream if stream.exists() else None


REGISTRY.register(ClaudeAdapter())
REGISTRY.register(CodexAdapter())
REGISTRY.register(GeminiAdapter())
