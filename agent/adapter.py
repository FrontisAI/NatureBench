"""Agent adapter interface and registry for NatureBench.

NatureBench is harness-agnostic at the protocol level: every task runs in a
container with held-out data, and the agent submits predictions to a host-side
evaluation service. The built-in Claude Code / Codex / Gemini CLIs are wired in
through :class:`AgentAdapter` subclasses; a custom agent is added the same way,
without editing ``solve.py``.

A custom agent implements ``name``, :meth:`AgentAdapter.system_prompt`, and
:meth:`AgentAdapter.build_command`; the two judge-transcript hooks are optional
and default to "no transcript". The interface deliberately exposes only what
``solve.py``/``judge.py`` actually consume — container mounts/env and the
built-in CLIs' resume/session machinery are *not* adapter extension points (see
``docs/custom-agents.md`` for how a custom agent handles credentials, mounts,
and proxy).

See ``docs/custom-agents.md`` for the authoring guide.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional


@dataclass
class AgentRunContext:
    """Inputs an adapter needs to build the prompt and in-container command.

    Populated by ``solve.py`` for a single task run. Custom adapters typically
    only read ``system_prompt``, ``model``, and the task/eval fields; the
    ``codex_*`` fields exist so the built-in Codex adapter can reproduce its
    exact invocation.
    """

    system_prompt: str
    model: str
    mode: str = "base"
    task_name: str = ""
    batch_name: str = ""
    eval_service_url: str = ""
    eval_output_dir: str = ""
    time_limit_minutes: int = 60
    # Host-side per-run directories (useful for an agent that mounts a per-task
    # path via ``docker_mounts``).
    task_out_dir: Optional[Path] = None
    workspace_dir: Optional[Path] = None
    is_resume: bool = False
    # Claude / Gemini session uuid (fresh-pinned or resume target).
    session_id: Optional[str] = None
    # Codex-specific auth / resume state.
    codex_resume_sid: Optional[str] = None
    codex_use_api_key: bool = False
    codex_api_base_url: Optional[str] = None
    codex_state_active: bool = False


class AgentAdapter(ABC):
    """Base class every NatureBench agent integration implements."""

    #: CLI selector, e.g. ``"claude"``. Must be unique within the registry.
    name: str = ""

    # -- prompt -----------------------------------------------------------
    @abstractmethod
    def system_prompt(self, ctx: AgentRunContext) -> str:
        """Return the prompt handed to the agent for this run.

        Built-in adapters return a resume notice when ``ctx.is_resume`` and the
        full task prompt otherwise.
        """

    # -- in-container command --------------------------------------------
    @abstractmethod
    def build_command(self, ctx: AgentRunContext) -> List[str]:
        """Return the argv executed inside the task container.

        The value flows straight into ``docker_cmd.extend(...)`` in solve.py.
        """

    # -- docker run integration (optional) -------------------------------
    def docker_mounts(self, ctx: AgentRunContext) -> List[str]:
        """Extra ``docker run`` mount arguments (a flat ``-v src:dst`` list).

        ``build_command`` returns the in-container argv and cannot add mounts,
        so an agent that needs a host path inside the container (e.g. its own
        auth/state dir) declares it here. Defaults to none; ``/task/problem``
        (read-only) and ``/workspace`` are mounted for every agent regardless.
        """
        return []

    def extra_env(self, ctx: AgentRunContext) -> List[str]:
        """Extra ``docker run`` env arguments (a flat ``-e KEY=VALUE`` list).

        For an agent that needs an environment variable beyond the
        Anthropic/OpenAI/Gemini keys solve.py already forwards. Defaults to none.
        """
        return []

    # -- judge transcript (optional) -------------------------------------
    def transcript_path(self, task_out_dir: Path) -> Optional[Path]:
        """Path to this agent's conversation record for the post-hoc judge.

        Return ``None`` (the default) if the agent produces no machine-readable
        transcript; the judge then reviews the workspace code alone. There is no
        implicit ``<name>.jsonl`` fallback — each agent declares its own log.
        """
        return None

    def transcript_excerptor(self) -> Optional[Callable[[Path], str]]:
        """Optional custom parser turning a transcript file into a judge excerpt.

        Return ``None`` (the default) to use the built-in excerptor, whose
        format sniffing recognizes the Claude/Codex/Gemini CLI logs. A custom
        agent whose transcript is in an unrecognized format can supply its own
        callable here so its conversation history reaches the judge instead of
        being skipped.
        """
        return None


class AgentRegistry:
    """Name → adapter-instance registry."""

    def __init__(self) -> None:
        self._adapters: Dict[str, AgentAdapter] = {}

    def register(self, adapter: AgentAdapter) -> AgentAdapter:
        if not adapter.name:
            raise ValueError("AgentAdapter.name must be a non-empty string")
        if adapter.name in self._adapters:
            raise ValueError(f"agent '{adapter.name}' is already registered")
        self._adapters[adapter.name] = adapter
        return adapter

    def get(self, name: str) -> AgentAdapter:
        try:
            return self._adapters[name]
        except KeyError:
            raise ValueError(
                f"unknown agent '{name}'. Registered agents: {self.names()}"
            ) from None

    def has(self, name: str) -> bool:
        return name in self._adapters

    def names(self) -> List[str]:
        return sorted(self._adapters)


#: Process-wide registry. Built-in adapters register themselves on import of
#: ``agent.cli_adapters``; custom agents call ``REGISTRY.register(...)``.
REGISTRY = AgentRegistry()
