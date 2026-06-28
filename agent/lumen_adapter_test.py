"""Tests for the Lumen agent adapter.

These pin the contract solve.py relies on: the adapter registers under "lumen",
its system prompt carries the NatureBench eval protocol, and its in-container
command writes a lumen.toml + launches `lumen run` non-interactively with the
task prompt as the positional argument.
"""
from __future__ import annotations

import os

import pytest

import agent  # noqa: F401  (importing the package registers the adapter)
from agent.adapter import REGISTRY, AgentRunContext


def _ctx(**overrides) -> AgentRunContext:
    base = dict(
        system_prompt="",
        model="deepseek-chat",
        mode="base",
        task_name="some_task",
        batch_name="some_batch",
        eval_service_url="http://host.docker.internal:9000",
        eval_output_dir="/workspace/output",
        time_limit_minutes=60,
    )
    base.update(overrides)
    return AgentRunContext(**base)


def test_adapter_is_registered():
    assert REGISTRY.has("lumen")
    assert "lumen" in REGISTRY.names()


def test_system_prompt_carries_eval_protocol():
    ctx = _ctx()
    prompt = REGISTRY.get("lumen").system_prompt(ctx)
    assert ctx.eval_service_url in prompt
    assert ctx.task_name in prompt
    assert "/evaluate" in prompt


def test_system_prompt_resume_is_a_notice():
    prompt = REGISTRY.get("lumen").system_prompt(_ctx(is_resume=True))
    assert "RESUME NOTICE" in prompt


def test_build_command_shape_and_prompt_passthrough():
    ctx = _ctx(system_prompt="THE-SYSTEM-PROMPT\nwith newlines")
    cmd = REGISTRY.get("lumen").build_command(ctx)
    # bash -lc <script> <argv0> <prompt>
    assert cmd[0] == "bash"
    assert cmd[1] == "-lc"
    # The (possibly huge, multi-line) prompt is the last argv element verbatim,
    # so solve.py's shlex-quote makes it land in the script's "$1".
    assert cmd[-1] == ctx.system_prompt
    script = cmd[2]
    assert 'lumen run --mode bypass "$1"' in script
    assert "lumen.toml" in script


def test_build_command_embeds_requested_model():
    cmd = REGISTRY.get("lumen").build_command(_ctx(model="deepseek-reasoner"))
    assert 'model = "deepseek-reasoner"' in cmd[2]
    assert 'profile = "core"' in cmd[2]  # no web tools


def test_extra_env_forwards_deepseek_key(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-xyz")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    env = REGISTRY.get("lumen").extra_env(_ctx())
    assert env == ["-e", "DEEPSEEK_API_KEY=sk-xyz"]


def test_extra_env_empty_without_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    assert REGISTRY.get("lumen").extra_env(_ctx()) == []


def test_base_url_override_flows_into_config(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "http://localhost:1234/v1")
    cmd = REGISTRY.get("lumen").build_command(_ctx())
    assert 'base_url = "http://localhost:1234/v1"' in cmd[2]
