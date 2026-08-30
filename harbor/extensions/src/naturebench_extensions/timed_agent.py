from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from pathlib import Path
from typing import Any, override

try:
    from harbor.agents.base import BaseAgent
    from harbor.agents.factory import AgentFactory
    from harbor.environments.base import BaseEnvironment
    from harbor.models.agent.context import AgentContext
    from harbor.models.agent.name import AgentName
    from harbor.trial.errors import AgentTimeoutError
except ImportError as error:  # pragma: no cover - exercised only without Harbor installed
    raise ImportError("NatureBenchTimedAgent requires the optional 'harbor' dependencies") from error


def _naturebench_defaults(inner_agent: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(kwargs)
    if inner_agent == "claude-code":
        resolved.setdefault("disallowed_tools", "WebSearch,WebFetch")
    elif inner_agent == "codex":
        resolved.setdefault("web_search", "disabled")
    return resolved


class NatureBenchTimedAgent(BaseAgent):
    """Host-side Harbor agent wrapper for NatureBench effective-time semantics."""

    SUPPORTS_ATIF = True

    @staticmethod
    @override
    def name() -> str:
        return "naturebench-timed-agent"

    def __init__(
        self,
        logs_dir: Path,
        model_name: str | None = None,
        logger: logging.Logger | None = None,
        mcp_servers=None,
        skills_dir: str | None = None,
        *args: Any,
        extra_env: dict[str, str] | None = None,
        inner_agent: str = "claude-code",
        timeout: float = 14400,
        **inner_kwargs: Any,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.inner_agent_name = inner_agent
        self.timeout = float(timeout)
        forwarded = _naturebench_defaults(inner_agent, inner_kwargs)
        super().__init__(
            logs_dir=logs_dir,
            model_name=model_name,
            logger=logger,
            mcp_servers=mcp_servers,
            skills_dir=skills_dir,
            *args,
            extra_env=extra_env,
        )
        common = {
            "logs_dir": self.logs_dir,
            "model_name": self.model_name,
            "logger": self.logger,
            "mcp_servers": self.mcp_servers,
            "skills_dir": self.skills_dir,
            "extra_env": self.extra_env,
        }
        if ":" in inner_agent:
            self.inner = AgentFactory.create_agent_from_import_path(
                inner_agent, **common, **forwarded
            )
        else:
            try:
                name = AgentName(inner_agent)
            except ValueError as error:
                raise ValueError(f"unknown inner_agent: {inner_agent}") from error
            self.inner = AgentFactory.create_agent_from_name(name, **common, **forwarded)

    @override
    def version(self) -> str | None:
        inner_version = self.inner.version() or "unknown"
        return f"0.1.0+{self.inner.name()}-{inner_version}"

    @override
    def to_agent_info(self):
        return self.inner.to_agent_info()

    @override
    async def setup(self, environment: BaseEnvironment) -> None:
        await self.inner.setup(environment)

    def _instruction_with_timeout(self, instruction: str) -> str:
        minutes = self.timeout / 60
        rendered = f"{minutes:g}"
        return instruction.replace(
            "You have **240 minutes** in total.",
            f"You have **{rendered} minutes** in total.",
        )

    async def _timer_command(self, environment: BaseEnvironment, command: str, timeout_sec: int | None = None):
        result = await environment.service_exec(
            f"/opt/naturebench/bin/timerctl {command}",
            service="naturebench-eval",
            timeout_sec=timeout_sec,
            user="root",
        )
        if result.return_code != 0:
            raise RuntimeError(
                f"timerctl {command} failed: {result.stderr or result.stdout or result.return_code}"
            )
        return result

    @override
    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        await self._timer_command(
            environment, f"start --timeout-seconds {self.timeout:g}", timeout_sec=30
        )
        agent_task = asyncio.create_task(
            self.inner.run(self._instruction_with_timeout(instruction), environment, context)
        )
        expiry_task = asyncio.create_task(
            self._timer_command(environment, "wait-expired", timeout_sec=None)
        )
        expired = False
        try:
            done, _ = await asyncio.wait(
                {agent_task, expiry_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if expiry_task in done:
                expired = True
                agent_task.cancel()
                with suppress(asyncio.CancelledError):
                    await agent_task
            else:
                expiry_task.cancel()
                with suppress(asyncio.CancelledError):
                    await expiry_task
                await agent_task
        finally:
            if not agent_task.done():
                agent_task.cancel()
                with suppress(asyncio.CancelledError):
                    await agent_task
            if not expiry_task.done():
                expiry_task.cancel()
                with suppress(asyncio.CancelledError):
                    await expiry_task
            await asyncio.shield(self._timer_command(environment, "stop", timeout_sec=30))
        if expired:
            raise AgentTimeoutError(
                f"NatureBench effective-time budget exhausted after {self.timeout:g} seconds"
            )

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
        self.inner.populate_context_post_run(context)
