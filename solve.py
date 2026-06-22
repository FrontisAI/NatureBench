"""solve.py — drive coding agents to solve NatureBench task packages.

Architecture overview:
  1. Start the Evaluation Service (HTTP) on the host
  2. Launch a solver container for each task
  3. Container mounts: /task/problem/ (read-only), /workspace (read-write)
  4. The evaluation/ directory is not mounted into the container (the agent cannot see the answers directly)
  5. Start the agent CLI inside the container (claude/codex)
  6. The agent calls the Evaluation Service over HTTP to get scores and iterate
  7. After the timeout the container is force-stopped, and the best score becomes the final score

Usage:
    python solve.py --config config.yaml
    python solve.py --task-set ./task-set/cpu.txt --data-dir ./data/tasks --out-dir ./results --agent claude --model <model>
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import queue
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
import urllib.parse
import uuid as _uuid_mod
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from config_loader import load_yaml_config, merge_args_with_config
from eval_service import ScoreTracker, start_server_background
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [solve] %(levelname)s %(message)s",
)
logger = logging.getLogger("cns_bench.solve")


_CODEX_HOME = "/tmp/codex-home"


# ---------------------------------------------------------------------------
# Task-set reader (shared with eval.py)
# ---------------------------------------------------------------------------

def _read_task_set(task_file: Path) -> List[str]:
    """Read task names from a text file (one per line, or JSON lines)."""
    if not task_file.exists():
        raise FileNotFoundError(f"Task list file not found: {task_file}")

    tasks: List[str] = []
    with task_file.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                spec = json.loads(line)
                task_name = (
                    spec.get("task_name")
                    or spec.get("name")
                    or spec.get("task_file")
                )
                if not task_name:
                    raise ValueError
                tasks.append(task_name)
                continue
            except (json.JSONDecodeError, ValueError):
                pass
            tasks.append(line)

    if not tasks:
        raise ValueError(f"No tasks found inside {task_file}")
    return tasks


# ---------------------------------------------------------------------------
# Docker helpers
# ---------------------------------------------------------------------------

@dataclass
class DockerfileSpec:
    """Parsed Dockerfile instructions for skip-build mode."""
    run_commands: List[str] = field(default_factory=list)   # Shell commands from RUN
    env_vars: Dict[str, str] = field(default_factory=dict)  # ENV key=value
    copy_srcs: List[Tuple[str, str]] = field(default_factory=list)  # (src, dest) from COPY/ADD


def _parse_dockerfile(dockerfile: Path) -> DockerfileSpec:
    """Parse a task Dockerfile into structured instructions.

    Handles: RUN (pip, apt-get, wget, git+, etc.), COPY/ADD, ENV.
    Skips: FROM, comments, blank lines.
    """
    spec = DockerfileSpec()
    if not dockerfile.exists():
        return spec

    text = dockerfile.read_text(encoding="utf-8")

    # Join backslash-continued lines
    text = text.replace("\\\n", " ")

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        upper = line.upper()

        if upper.startswith("FROM"):
            continue

        if upper.startswith("RUN "):
            # Preserve the full shell command (apt-get, pip, wget, etc.)
            cmd = line[4:].strip()
            if cmd:
                spec.run_commands.append(cmd)

        elif upper.startswith("ENV "):
            # ENV KEY=VALUE or ENV KEY VALUE
            rest = line[4:].strip()
            if "=" in rest:
                key, _, val = rest.partition("=")
                spec.env_vars[key.strip()] = val.strip().strip('"')
            else:
                parts = rest.split(None, 1)
                if len(parts) == 2:
                    spec.env_vars[parts[0]] = parts[1].strip('"')

        elif upper.startswith("COPY ") or upper.startswith("ADD "):
            prefix_len = 5 if upper.startswith("COPY ") else 4
            rest = line[prefix_len:].strip()
            parts = rest.split()
            if len(parts) >= 2:
                spec.copy_srcs.append((parts[0], parts[-1]))

    return spec


def _ensure_clash_proxy_container(
    container_name: str,
    network_name: str,
) -> None:
    """Validate that a shared Clash proxy container exists on the target network."""
    inspect = subprocess.run(
        ["docker", "inspect", container_name],
        capture_output=True,
        text=True,
    )
    if inspect.returncode != 0:
        raise RuntimeError(
            f"Clash proxy container {container_name!r} does not exist. "
            "Create it first before enabling Codex proxying."
        )

    try:
        payload = json.loads(inspect.stdout)[0]
    except (json.JSONDecodeError, IndexError, KeyError) as exc:
        raise RuntimeError(
            f"Failed to inspect Clash proxy container {container_name!r}: {exc}"
        ) from exc

    running = bool(payload.get("State", {}).get("Running"))
    networks = payload.get("NetworkSettings", {}).get("Networks", {}) or {}
    if not running:
        raise RuntimeError(
            f"Clash proxy container {container_name!r} is not running. "
            "Start it first before enabling Codex proxying."
        )
    if network_name not in networks:
        joined = ", ".join(sorted(networks)) or "<none>"
        raise RuntimeError(
            f"Clash proxy container {container_name!r} is not attached to Docker "
            f"network {network_name!r} (current: {joined})."
        )



def _host_proxy_env_args() -> List[str]:
    """Pass through standard host proxy environment variables when present."""
    args: List[str] = []
    for key in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
        "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    ):
        val = os.environ.get(key)
        if val:
            args.extend(["-e", f"{key}={val}"])
    return args



def _codex_auth_mount_args(codex_state_dir: Path) -> List[str]:
    """Mount per-task Codex state (auth + sessions) into the container's HOME."""
    return [
        "-v", f"{str(codex_state_dir)}:{_CODEX_HOME}/.codex",
    ]



def _prepare_task_codex_state_dir(
    task_out_dir: Path,
    source_auth_dir: Path,
    *,
    reseed: bool,
) -> Path:
    """Seed an isolated Codex state directory (auth + sessions) per task.

    Fresh runs (reseed=True) wipe any prior state and copy **only** the auth
    files the CLI needs (`auth.json`, `config.toml`). Session history stays
    empty so that ``_capture_codex_session_id`` cannot pick a stale sid from
    the host.

    Resume runs (reseed=False) require the prior state dir to still exist;
    never silently re-bootstrap it.
    """
    state_dir = task_out_dir / ".codex_state"
    if not reseed:
        if not state_dir.is_dir():
            raise RuntimeError(
                f"Codex resume requested but {state_dir} is missing"
            )
        return state_dir
    if state_dir.exists():
        shutil.rmtree(state_dir)
    state_dir.mkdir(parents=True)
    for name in ("auth.json", "config.toml"):
        src = source_auth_dir / name
        if src.is_file():
            shutil.copy2(src, state_dir / name)
    (state_dir / "sessions").mkdir(exist_ok=True)
    return state_dir



def _codex_exec_cmd(base_cmd: List[str]) -> List[str]:
    """Run Codex with a dedicated HOME so auth lookup is explicit."""
    return ["env", f"HOME={_CODEX_HOME}", *base_cmd]



def _proxy_env_args(
    proxy_host: str,
    http_port: int,
    socks_port: int,
) -> List[str]:
    """Build proxy env args for a Codex container.

    ``proxy_host`` is the address visible from inside the task container —
    use ``127.0.0.1`` for embedded mode (clash runs in the same network
    namespace) or the sidecar container name for sidecar mode.
    """
    http_proxy = f"http://{proxy_host}:{http_port}"
    socks_proxy = f"socks5://{proxy_host}:{socks_port}"
    no_proxy_value = "127.0.0.1,localhost,::1,host.docker.internal"
    merged_no_proxy = []
    for key in ("NO_PROXY", "no_proxy"):
        val = os.environ.get(key)
        if val:
            merged_no_proxy.extend([x.strip() for x in val.split(",") if x.strip()])
    if merged_no_proxy:
        merged_no_proxy = list(dict.fromkeys(no_proxy_value.split(",") + merged_no_proxy))
        no_proxy_value = ",".join(merged_no_proxy)
    return [
        "-e", f"HTTP_PROXY={http_proxy}",
        "-e", f"HTTPS_PROXY={http_proxy}",
        "-e", f"ALL_PROXY={socks_proxy}",
        "-e", f"NO_PROXY={no_proxy_value}",
        "-e", f"http_proxy={http_proxy}",
        "-e", f"https_proxy={http_proxy}",
        "-e", f"all_proxy={socks_proxy}",
        "-e", f"no_proxy={no_proxy_value}",
    ]


def _embedded_clash_setup_cmds() -> List[str]:
    """Setup commands that bring up the in-container Clash proxy.

    The bundle is mounted read-only at /clash-bundle; clash needs a writable
    config dir for its cache.db, so we copy into /tmp/clash-rw first.

    Each returned string is joined with ``&&`` by the caller, so avoid bare
    ``&`` backgrounding mid-chain (that would create ``& &&`` which is a
    bash parse error). The backgrounded launch + readiness loop is wrapped
    into a single subshell entry.
    """
    launch_and_wait = (
        "{ "
        "nohup /clash-bundle/clash -d /tmp/clash-rw > /tmp/clash.log 2>&1 & "
        "for i in $(seq 1 60); do "
        "  curl -sf -m 1 http://127.0.0.1:9090/version >/dev/null 2>&1 && break; "
        "  sleep 0.5; "
        "done; "
        "curl -sf -m 1 http://127.0.0.1:9090/version >/dev/null "
        "|| { echo '[clash] failed to start' >&2; tail -50 /tmp/clash.log >&2; exit 1; }; "
        "}"
    )
    return [
        "mkdir -p /tmp/clash-rw",
        "cp -r /clash-bundle/config/. /tmp/clash-rw/",
        launch_and_wait,
    ]



def _probe_codex_login(
    image_tag: str,
    codex_auth_dir: Path,
    proxy_mode: str = "host",
    proxy_container: Optional[str] = None,
    proxy_network: Optional[str] = None,
    proxy_bundle: Optional[Path] = None,
    proxy_http_port: int = 7890,
    proxy_socks_port: int = 7891,
) -> None:
    """Verify that Codex login state is usable in the same image/env as the task.

    ``proxy_mode`` selects how the probe reaches the network:
      * ``host``     — pass host proxy environment variables
      * ``none``     — no proxy, direct egress
      * ``sidecar``  — attach to ``proxy_network`` and use the
        ``proxy_container`` container name as proxy host
      * ``embedded`` — mount ``proxy_bundle`` and start clash inside
        the probe container before running ``codex login status``
    """
    probe_cmd: List[str] = ["docker", "run", "--rm"]
    if proxy_mode == "sidecar":
        if not proxy_container or not proxy_network:
            raise ValueError(
                "sidecar proxy mode requires proxy_container and proxy_network"
            )
        probe_cmd.extend(["--network", proxy_network])
    if platform.system() == "Linux":
        probe_cmd.extend(["--add-host=host.docker.internal:host-gateway"])

    if proxy_mode == "sidecar":
        probe_cmd.extend(
            _proxy_env_args(
                proxy_container,
                proxy_http_port,
                proxy_socks_port,
            )
        )
    elif proxy_mode == "embedded":
        if not proxy_bundle or not proxy_bundle.is_dir():
            raise ValueError(
                f"embedded proxy mode requires a clash bundle dir; got {proxy_bundle}"
            )
        probe_cmd.extend([
            "-v", f"{str(proxy_bundle.resolve())}:/clash-bundle:ro",
        ])
        probe_cmd.extend(
            _proxy_env_args(
                "127.0.0.1",
                proxy_http_port,
                proxy_socks_port,
            )
        )
    elif proxy_mode == "host":
        probe_cmd.extend(_host_proxy_env_args())

    probe_cmd.extend(_codex_auth_mount_args(codex_auth_dir))
    if proxy_mode == "embedded":
        clash_setup = " && ".join(_embedded_clash_setup_cmds())
        inner = f"{clash_setup} && HOME={_CODEX_HOME} codex login status"
    else:
        inner = f"HOME={_CODEX_HOME} codex login status"
    probe_cmd.extend([
        "--entrypoint", "/bin/bash",
        image_tag,
        "-lc", inner,
    ])
    probe = subprocess.run(probe_cmd, capture_output=True, text=True)
    if probe.returncode != 0:
        output = (probe.stdout + "\n" + probe.stderr).strip()
        if "not logged in" in output.lower() or "login" in output.lower():
            hint = "Codex auth dir is not logged in"
        else:
            hint = "Codex probe failed"
        raise RuntimeError(
            f"{hint}. Run `codex login --device-auth` once on the host and ensure {codex_auth_dir} "
            f"contains the login state; status output: {probe.stdout[-200:]} {probe.stderr[-200:]}"
        )



def _ensure_task_image(task_name: str, data_dir: Path, base_image: str = "naturebench-base:v3", dockerfile_name: str = "Dockerfile.v3") -> str:
    """Ensure naturebench-task-<task>:base image exists. Build from Dockerfile if needed."""
    image_tag = f"naturebench-task-{task_name}:base"

    # Check if image already exists
    result = subprocess.run(
        ["docker", "images", "-q", image_tag],
        capture_output=True, text=True,
    )
    if result.stdout.strip():
        logger.info("[%s] Image %s already exists", task_name, image_tag)
        return image_tag

    # Try to build from task Dockerfile
    dockerfile = data_dir / task_name / "environment" / dockerfile_name
    if dockerfile.exists():
        logger.info("[%s] Building image %s from %s", task_name, image_tag, dockerfile)
        build_cmd = [
            "docker", "build",
            "-t", image_tag,
            "-f", str(dockerfile.resolve()),
            str(dockerfile.parent.resolve()),
        ]
        proc = subprocess.run(build_cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            logger.error("[%s] Docker build failed:\n%s", task_name, proc.stderr[-2000:])
            raise RuntimeError(f"Failed to build image {image_tag}")
        logger.info("[%s] Image built: %s", task_name, image_tag)
        return image_tag

    # Fall back to base image
    logger.warning("[%s] No Dockerfile found, using %s", task_name, base_image)
    return base_image


def _remove_container(container_name: str) -> None:
    """Force remove a container if it exists."""
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True, text=True,
    )


# ---------------------------------------------------------------------------
# Agent CLI command builders
# ---------------------------------------------------------------------------

def _build_claude_cmd(
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


def _build_gemini_cmd(
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


def _build_codex_cmd(
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


# ---------------------------------------------------------------------------
# Single-task solver
# ---------------------------------------------------------------------------


def _host_url(eval_service_url: str) -> str:
    """Convert the container-visible host.docker.internal URL to the host localhost URL."""
    return eval_service_url.replace("host.docker.internal", "localhost")


# ---------------------------------------------------------------------------
# Resume support helpers
# ---------------------------------------------------------------------------

# Default Claude Code mounts ~/.claude → /root/.claude inside the container.
# We pin the workspace cwd to /workspace, so the CLI stores its session jsonl at
# `~/.claude/projects/-workspace/<sid>.jsonl`.
# Claude resume prompt: minimal notice (claude does not need Session Rules,
# and does not need extra time-budget reminders — the time-budget bullet is
# already in CLAUDE_BASE_PROMPT and claude tends to use the full time anyway).
_RESUME_PROMPT_CLAUDE = (
    "[RESUME NOTICE] You were previously interrupted on this task. "
    "The /workspace contents and any prior /evaluate submissions are preserved. "
    "Continue from where you left off. "
    "Check `/time_remaining` first before deciding what to do next."
)

# Codex resume prompt: re-inject the Session Rules block (the in-container codex
# CLI re-reads the system prompt fresh on resume) PLUS a time-budget reminder
# (codex tends to exit early; this counters that on resume runs).
_RESUME_PROMPT_CODEX = (
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
_RESUME_PROMPT_GEMINI = (
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

# Backward-compat alias (in case anything still imports the old name).
_RESUME_PROMPT = _RESUME_PROMPT_CLAUDE


def _setup_session_id(
    task_out_dir: Path,
    task_name: str,
    is_resume: bool,
) -> str:
    """Return the Claude session UUID for this task.

    Behavior:
      * is_resume=True  : require existing claude_session_id.txt; raise if missing.
      * is_resume=False : if a sid file already exists, archive it with a timestamp
                          suffix (.bak.<epoch>) before writing a fresh UUID, so we
                          never silently clobber a recoverable session.
    """
    sid_file = task_out_dir / "claude_session_id.txt"
    if is_resume:
        if not sid_file.exists():
            raise RuntimeError(
                f"[{task_name}] resume requested but {sid_file} not found"
            )
        return sid_file.read_text(encoding="utf-8").strip()

    if sid_file.exists():
        bak = sid_file.with_suffix(f".bak.{int(time.time())}")
        sid_file.rename(bak)
        logger.warning(
            "[%s] archived previous session id to %s (fresh run requested)",
            task_name, bak.name,
        )
    new_sid = str(_uuid_mod.uuid4())
    sid_file.write_text(new_sid, encoding="utf-8")
    return new_sid


def _capture_codex_session_id(
    state_dir: Path,
    *,
    since_mtime: float = 0.0,
) -> Optional[str]:
    """Extract this run's Codex session UUID from the per-task state dir.

    Only filenames are inspected and files older than ``since_mtime`` are
    skipped, to avoid grabbing a stale sid from a seeded session file.
    """
    sessions = state_dir / "sessions"
    if not sessions.is_dir():
        return None
    sid_re = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
    candidates: List[Tuple[float, Path]] = []
    for f in sessions.rglob("*"):
        if not f.is_file():
            continue
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        if mtime < since_mtime:
            continue
        candidates.append((mtime, f))
    candidates.sort(reverse=True)
    for _, f in candidates:
        m = sid_re.search(f.name)
        if m:
            return m.group(0)
    return None



def _capture_gemini_session_id(jsonl_path: Path) -> Optional[str]:
    """Parse the stream-json init event from gemini.jsonl and return its UUID.

    Gemini CLI's first stdout line in --output-format=stream-json mode is an
    ``init`` event that contains ``session_id``. We scan early lines (defensive
    against minor format variations) and return the first uuid we find.
    """
    if not jsonl_path.exists():
        return None
    sid_re = re.compile(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )
    try:
        with jsonl_path.open("r", encoding="utf-8", errors="replace") as f:
            for _ in range(64):
                line = f.readline()
                if not line:
                    break
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") == "init":
                    sid = obj.get("session_id")
                    if isinstance(sid, str) and sid_re.fullmatch(sid):
                        return sid
                # Fallback: any top-level "session_id" that looks like a uuid
                sid = obj.get("session_id") if isinstance(obj, dict) else None
                if isinstance(sid, str) and sid_re.fullmatch(sid):
                    return sid
    except OSError:
        return None
    return None


def _has_prior_state(task_out_dir: Path) -> bool:
    """Return True if the task directory already contains state from a prior run."""
    for name in (
        "result.json",
        "submissions.jsonl",
        "claude_session_id.txt",
        ".claude_state",
        "codex_session_id.txt",
        ".codex_state",
        "claude.jsonl",
        "claude.err",
        "codex.jsonl",
        "codex.err",
        "judge_verdict.json",
    ):
        if (task_out_dir / name).exists():
            return True
    return False


def _archive_prior_state_for_force_fresh(task_out_dir: Path, task_name: str) -> None:
    """For --force-fresh: move all stateful artifacts out of the way (no delete)
    so that the next fresh run starts from clean. We rename rather than rm -rf
    to keep history recoverable.
    """
    ts = int(time.time())
    bak_root = task_out_dir / f"_force_fresh_archive_{ts}"
    moved = []
    for name in (
        "result.json",
        "submissions.jsonl",
        "claude_session_id.txt",
        ".claude_state",
        "codex_session_id.txt",
        ".codex_state",
        "claude.jsonl",
        "claude.err",
        "codex.jsonl",
        "codex.err",
        "judge_verdict.json",
    ):
        src = task_out_dir / name
        if src.exists():
            bak_root.mkdir(parents=True, exist_ok=True)
            src.rename(bak_root / name)
            moved.append(name)
    if moved:
        logger.warning(
            "[%s] --force-fresh: archived %d artifact(s) into %s/",
            task_name, len(moved), bak_root.name,
        )


def _setup_gemini_session_id(
    task_out_dir: Path,
    task_name: str,
    is_resume: bool,
) -> Optional[str]:
    """Return the Gemini session UUID for this task, or None for a fresh run.

    Gemini CLI does NOT support pinning a fresh session to a caller-supplied
    UUID (no --session-id flag). On fresh runs we therefore let the CLI
    generate its own session id; ``_capture_gemini_session_id`` is responsible
    for writing the real id to gemini_session_id.txt after the run completes.

    On resume we require gemini_session_id.txt to exist and pass its uuid via
    ``--resume <uuid>``.
    """
    sid_file = task_out_dir / "gemini_session_id.txt"
    if is_resume:
        if not sid_file.exists():
            raise RuntimeError(
                f"[{task_name}] gemini resume requested but {sid_file} not found"
            )
        return sid_file.read_text(encoding="utf-8").strip()
    # Fresh run — archive old sid file (if any) so a previous run's id is not
    # mistaken for the current one. The CLI itself will allocate a new UUID;
    # we capture it from the stream-json ``init`` event after the run finishes.
    if sid_file.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        sid_file.rename(task_out_dir / f"gemini_session_id_{ts}.txt.bak")
    return None


def _load_resume_history(task_out_dir: Path) -> List[Dict[str, Any]]:
    """Read the cumulative resume_history from the existing result.json (if any)."""
    res_path = task_out_dir / "result.json"
    if not res_path.exists():
        return []
    try:
        old = json.loads(res_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    history = old.get("resume_history") or []
    if not isinstance(history, list):
        return []
    return history


def _resume_eligible(task_out_dir: Path, agent_name: str) -> Tuple[bool, str]:
    """Decide whether a task is eligible for resume.

    Returns (ok, reason). Caller is expected to use this for soft validation
    only — final guard is `_setup_session_id` requiring sid file.
    """
    res_path = task_out_dir / "result.json"
    if not res_path.exists():
        return False, "no prior result.json"
    if agent_name == "claude":
        sid_path = task_out_dir / "claude_session_id.txt"
        state_path = task_out_dir / ".claude_state"
        if not sid_path.exists():
            return False, "no claude_session_id.txt"
        if not state_path.exists():
            return False, "no .claude_state directory"
        return True, "ok"
    if agent_name == "codex":
        sid_path = task_out_dir / "codex_session_id.txt"
        state_path = task_out_dir / ".codex_state"
        if not sid_path.exists():
            return False, "no codex_session_id.txt"
        if not state_path.exists():
            return False, "no .codex_state directory"
        return True, "ok"
    if agent_name == "gemini":
        sid_path = task_out_dir / "gemini_session_id.txt"
        state_path = task_out_dir / ".gemini_state"
        if not sid_path.exists():
            return False, "no gemini_session_id.txt"
        if not state_path.exists():
            return False, "no .gemini_state directory"
        return True, "ok"
    return False, f"resume not supported for agent {agent_name}"


def _query_time_remaining(eval_service_url: str, task_name: str,
                          batch_name: Optional[str] = None) -> Optional[float]:
    """GET /time_remaining; return remaining seconds or None on error."""
    host_url = _host_url(eval_service_url)
    url = f"{host_url}/time_remaining?task_name={urllib.parse.quote(task_name)}"
    if batch_name:
        url += "&batch_name=" + urllib.parse.quote(batch_name)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data.get("remaining_seconds")
    except Exception as e:
        logger.warning("[%s] time_remaining query failed: %s", task_name, e)
        return None


def _notify_timer_resume(eval_service_url: str, task_name: str,
                         batch_name: Optional[str] = None) -> None:
    """POST /resume_timer; ignore failures (eval_service may not support it)."""
    host_url = _host_url(eval_service_url)
    url = f"{host_url}/resume_timer"
    body = {"task_name": task_name}
    if batch_name:
        body["batch_name"] = batch_name
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as _resp:
            _ = _resp.read()
    except Exception as e:
        logger.debug("[%s] /resume_timer not honored: %s", task_name, e)


def _notify_timer_pause(eval_service_url: str, task_name: str,
                        batch_name: Optional[str] = None) -> None:
    """POST /pause_timer when the agent container is stopping but the task is
    not "done" (i.e. could resume later). Ignore HTTP errors so legacy
    eval_service builds without /pause_timer don't break solve.py.
    """
    host_url = _host_url(eval_service_url)
    url = f"{host_url}/pause_timer"
    body = {"task_name": task_name}
    if batch_name:
        body["batch_name"] = batch_name
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as _resp:
            _ = _resp.read()
    except Exception as e:
        logger.debug("[%s] /pause_timer not honored: %s", task_name, e)


def _wait_eval_drain(eval_service_url: str, task_name: str,
                     batch_name: Optional[str] = None,
                     poll_interval: float = 2.0,
                     max_unreachable_polls: int = 30) -> bool:
    """Wait until the remote eval_service has no in-flight evaluator for task.

    In external-eval mode, solve.py's local tracker does not know the real
    active_evals count, so we must poll /time_remaining and wait for
    is_paused=False before calling /pause_timer. Otherwise /pause_timer is
    rejected with 409 while evaluator threads are still running, and the task
    timer keeps advancing after the agent container exits.

    There is intentionally NO fixed time cap: an evaluator invocation may run
    up to its own 3600s subprocess cap, so a short deadline would abandon a
    legitimately-running evaluation and re-introduce the timer leak this
    function exists to prevent. The wait terminates when:
      - is_paused flips to False (evaluation drained)        -> return True
      - the task is unknown (404)                            -> return True
      - the eval_service is unreachable for
        ``max_unreachable_polls`` consecutive polls           -> return False
        (the service is dead; there is no live timer left to protect).
    While the wait is in progress the task timer is already paused
    (active_evals > 0), so this wait does not consume the agent's solve budget.
    """
    host_url = _host_url(eval_service_url)
    url = f"{host_url}/time_remaining?task_name={urllib.parse.quote(task_name)}"
    if batch_name:
        url += "&batch_name=" + urllib.parse.quote(batch_name)
    unreachable = 0
    waited = 0.0
    while True:
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            unreachable = 0
            if not data.get("is_paused", False):
                return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return True
            # Service is alive (it answered), just an HTTP-level error.
            unreachable = 0
            logger.debug("[%s] drain poll HTTP error: %s", task_name, e)
        except Exception as e:
            unreachable += 1
            logger.debug("[%s] drain poll failed (%d/%d): %s",
                         task_name, unreachable, max_unreachable_polls, e)
            if unreachable >= max_unreachable_polls:
                logger.warning(
                    "[%s] eval_service unreachable for %d consecutive polls; "
                    "abandoning drain wait (/pause_timer may be skipped)",
                    task_name, unreachable,
                )
                return False
        time.sleep(poll_interval)
        waited += poll_interval
        if waited % 60 < poll_interval:
            logger.info(
                "[%s] still waiting for in-flight evaluation to drain (%.0fs)...",
                task_name, waited,
            )


# ---------------------------------------------------------------------------
# GPU pool (in-memory or cross-process file-backed)
# ---------------------------------------------------------------------------

@dataclass
class _GpuLease:
    """A single task's GPU allocation.

    `kind="normal"` means `gpu_id` came from the existing exclusive GPU pool.
    `kind="shared"` means `slot_id` came from the shared slot pool, while Docker
    still receives the full physical `gpu_id` via `--gpus device=<gpu_id>`.
    """

    gpu_id: int
    kind: str
    task_name: str
    slot_id: Optional[int] = None


class _InMemoryGpuPool:
    """Original single-process queue-based pool. `get(block=True)` blocks
    until a GPU is freed; `get(block=False)` raises queue.Empty."""

    def __init__(self, gpu_ids: List[int]) -> None:
        self._q: "queue.Queue[int]" = queue.Queue()
        for gid in gpu_ids:
            self._q.put(gid)

    def get(self, block: bool = True, timeout: Optional[float] = None) -> int:
        return self._q.get(block=block, timeout=timeout)

    def put(self, gid: int) -> None:
        self._q.put(gid)


class _FileGpuPool:
    """Cross-process GPU pool. Coordinates multiple solve.py instances via a
    JSON file under fcntl.flock. Acquire blocks until a GPU is free; release
    marks it free. Stale holders (dead pid) are auto-reclaimed.

    State file schema:
        {"gpus": {"<id>": {"holder_pid": int|null, "task": str|null,
                           "acquired_at": float|null}}}
    """

    POLL_INTERVAL = 1.0   # seconds between retries when blocked
    _PROBE_CACHE_TTL = 5.0  # seconds — reuse nvidia-smi result within this window

    def __init__(self, gpu_ids: List[int], pool_path: Path,
                 skip_busy_mb: int = 0, skip_busy_util: int = 100) -> None:
        import fcntl as _fcntl
        self._fcntl = _fcntl
        self._pool_path = pool_path
        self._lock_path = pool_path.with_suffix(pool_path.suffix + ".lock")
        self._registered: List[int] = list(gpu_ids)
        self._held: List[int] = []  # GPUs this process currently holds
        # External-busy detection thresholds. skip_busy_mb<=0 disables.
        self._skip_busy_mb = int(skip_busy_mb)
        self._skip_busy_util = int(skip_busy_util)
        self._probe_cache: Dict[int, tuple] = {}  # gid -> (mem_mb, util_pct, ts)
        # initialize / merge own gpu_ids into the file pool
        self._with_lock(lambda state: self._merge_ids(state, gpu_ids))

    def _probe_external_busy(self, gid: int) -> bool:
        """Return True if GPU `gid` is currently used by an *external* process
        (memory or utilization above thresholds). Cached for _PROBE_CACHE_TTL
        to limit nvidia-smi calls. Falls back to "not busy" on probe error.
        """
        if self._skip_busy_mb <= 0:
            return False
        now = time.time()
        cached = self._probe_cache.get(gid)
        if cached and (now - cached[2]) < self._PROBE_CACHE_TTL:
            mem_mb, util_pct, _ = cached
        else:
            try:
                out = subprocess.run(
                    ["nvidia-smi",
                     "--query-gpu=memory.used,utilization.gpu",
                     "--format=csv,noheader,nounits",
                     "-i", str(gid)],
                    capture_output=True, text=True, timeout=3,
                )
                if out.returncode != 0 or not out.stdout.strip():
                    return False
                parts = [p.strip() for p in out.stdout.strip().split(",")]
                mem_mb = int(parts[0])
                util_pct = int(parts[1])
                self._probe_cache[gid] = (mem_mb, util_pct, now)
            except Exception:
                return False
        return mem_mb > self._skip_busy_mb or util_pct > self._skip_busy_util

    def _open_lock(self):
        # open or create the lock file
        return open(self._lock_path, "a+")

    def _read_state(self) -> Dict[str, Any]:
        if not self._pool_path.exists():
            return {"gpus": {}}
        try:
            return json.loads(self._pool_path.read_text(encoding="utf-8"))
        except Exception:
            return {"gpus": {}}

    def _write_state(self, state: Dict[str, Any]) -> None:
        tmp = self._pool_path.with_suffix(self._pool_path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(self._pool_path)

    def _with_lock(self, fn):
        # exclusive lock around read-modify-write of pool file
        f = self._open_lock()
        try:
            self._fcntl.flock(f.fileno(), self._fcntl.LOCK_EX)
            state = self._read_state()
            ret = fn(state)
            self._write_state(state)
            return ret
        finally:
            try:
                self._fcntl.flock(f.fileno(), self._fcntl.LOCK_UN)
            finally:
                f.close()

    @staticmethod
    def _is_pid_alive(pid: Optional[int]) -> bool:
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _merge_ids(self, state: Dict[str, Any], gpu_ids: List[int]) -> None:
        gpus = state.setdefault("gpus", {})
        for gid in gpu_ids:
            key = str(gid)
            if key not in gpus:
                gpus[key] = {"holder_pid": None, "task": None, "acquired_at": None}

    def _try_acquire(self, state: Dict[str, Any]) -> Optional[int]:
        gpus = state.setdefault("gpus", {})
        # prefer GPUs we initially registered (own list) before others
        my_pid = os.getpid()
        for gid in self._registered + sorted(int(k) for k in gpus.keys() if int(k) not in self._registered):
            key = str(gid)
            entry = gpus.get(key)
            if entry is None:
                continue
            holder = entry.get("holder_pid")
            if holder is None or not self._is_pid_alive(holder):
                # Pool says this GPU is free, but check if an external process
                # (not in our pool) is using it. Skip in that case so we don't
                # contend with someone else's training.
                if self._probe_external_busy(gid):
                    continue
                # free or stale → take it
                entry["holder_pid"] = my_pid
                entry["acquired_at"] = time.time()
                return gid
        return None

    def get(self, block: bool = True, timeout: Optional[float] = None) -> int:
        deadline = (time.time() + timeout) if (timeout is not None) else None
        first = True
        while True:
            gid_holder = []
            def _take(state, _h=gid_holder):
                gid = self._try_acquire(state)
                _h.append(gid)
            self._with_lock(_take)
            gid = gid_holder[0]
            if gid is not None:
                self._held.append(gid)
                return gid
            if not block:
                raise queue.Empty()
            if deadline is not None and time.time() >= deadline:
                raise queue.Empty()
            if first:
                logger.info("GPU pool: all GPUs busy, waiting for one to free up...")
                first = False
            time.sleep(self.POLL_INTERVAL)

    def put(self, gid: int) -> None:
        my_pid = os.getpid()
        def _release(state):
            entry = state.get("gpus", {}).get(str(gid))
            if entry and entry.get("holder_pid") == my_pid:
                entry["holder_pid"] = None
                entry["acquired_at"] = None
        self._with_lock(_release)
        try:
            self._held.remove(gid)
        except ValueError:
            pass

    def release_all(self) -> None:
        """Best-effort cleanup on shutdown: release everything still held."""
        for gid in list(self._held):
            try:
                self.put(gid)
            except Exception:
                pass


def _build_gpu_pool(gpu_ids: List[int], pool_path: Optional[Path],
                    skip_busy_mb: int = 0, skip_busy_util: int = 100):
    if pool_path is None:
        return _InMemoryGpuPool(gpu_ids)
    pool_path.parent.mkdir(parents=True, exist_ok=True)
    return _FileGpuPool(gpu_ids, pool_path, skip_busy_mb=skip_busy_mb,
                        skip_busy_util=skip_busy_util)


class _FileSharedGpuSlotPool:
    """Cross-process slot pool for a selected low-GPU task subset.

    Unlike `_FileGpuPool`, one physical GPU can have multiple live holders. The
    file state tracks per-slot holders under a single GPU id:

        {
          "shared_gpus": {
            "<gpu_id>": {
              "capacity": int,
              "slots": {
                "0": {"holder_pid": int|null, "task": str|null,
                      "acquired_at": float|null},
                ...
              }
            }
          }
        }
    """

    POLL_INTERVAL = 1.0

    def __init__(self, gpu_id: int, slots: int, pool_path: Path) -> None:
        import fcntl as _fcntl
        if slots <= 0:
            raise ValueError("--shared-gpu-slots must be positive")
        self._fcntl = _fcntl
        self._gpu_id = int(gpu_id)
        self._slots = int(slots)
        self._pool_path = pool_path
        self._lock_path = pool_path.with_suffix(pool_path.suffix + ".lock")
        self._held: List[int] = []
        pool_path.parent.mkdir(parents=True, exist_ok=True)
        self._with_lock(self._merge_config)

    def _open_lock(self):
        return open(self._lock_path, "a+")

    def _read_state(self) -> Dict[str, Any]:
        if not self._pool_path.exists():
            return {"shared_gpus": {}}
        try:
            return json.loads(self._pool_path.read_text(encoding="utf-8"))
        except Exception:
            return {"shared_gpus": {}}

    def _write_state(self, state: Dict[str, Any]) -> None:
        tmp = self._pool_path.with_suffix(self._pool_path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(self._pool_path)

    def _with_lock(self, fn):
        f = self._open_lock()
        try:
            self._fcntl.flock(f.fileno(), self._fcntl.LOCK_EX)
            state = self._read_state()
            ret = fn(state)
            self._write_state(state)
            return ret
        finally:
            try:
                self._fcntl.flock(f.fileno(), self._fcntl.LOCK_UN)
            finally:
                f.close()

    @staticmethod
    def _is_pid_alive(pid: Optional[int]) -> bool:
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    @staticmethod
    def _clear_slot(slot: Dict[str, Any]) -> None:
        slot["holder_pid"] = None
        slot["task"] = None
        slot["acquired_at"] = None

    def _entry(self, state: Dict[str, Any]) -> Dict[str, Any]:
        shared = state.setdefault("shared_gpus", {})
        entry = shared.setdefault(str(self._gpu_id), {})
        entry.setdefault("capacity", self._slots)
        entry.setdefault("slots", {})
        return entry

    def _reclaim_stale(self, entry: Dict[str, Any]) -> None:
        for slot in entry.setdefault("slots", {}).values():
            holder = slot.get("holder_pid")
            if holder is not None and not self._is_pid_alive(holder):
                self._clear_slot(slot)

    def _merge_config(self, state: Dict[str, Any]) -> None:
        entry = self._entry(state)
        slots = entry.setdefault("slots", {})
        self._reclaim_stale(entry)

        old_capacity = int(entry.get("capacity") or self._slots)
        if old_capacity != self._slots:
            live_slots = []
            for sid, slot in slots.items():
                holder = slot.get("holder_pid")
                if holder is not None and self._is_pid_alive(holder):
                    live_slots.append(sid)
            if live_slots:
                raise RuntimeError(
                    f"shared GPU {self._gpu_id} pool capacity mismatch: "
                    f"existing={old_capacity}, requested={self._slots}, "
                    f"live_slots={','.join(sorted(live_slots))}"
                )
            entry["capacity"] = self._slots

        for slot_id in range(self._slots):
            slots.setdefault(
                str(slot_id),
                {"holder_pid": None, "task": None, "acquired_at": None},
            )
        for sid in list(slots.keys()):
            if int(sid) >= self._slots:
                slot = slots[sid]
                holder = slot.get("holder_pid")
                if holder is None or not self._is_pid_alive(holder):
                    del slots[sid]

    def _try_acquire(self, state: Dict[str, Any], task_name: str) -> Optional[_GpuLease]:
        entry = self._entry(state)
        self._merge_config(state)
        slots = entry.setdefault("slots", {})
        my_pid = os.getpid()
        for slot_id in range(self._slots):
            slot = slots[str(slot_id)]
            holder = slot.get("holder_pid")
            if holder is None or not self._is_pid_alive(holder):
                slot["holder_pid"] = my_pid
                slot["task"] = task_name
                slot["acquired_at"] = time.time()
                return _GpuLease(
                    gpu_id=self._gpu_id,
                    kind="shared",
                    task_name=task_name,
                    slot_id=slot_id,
                )
        return None

    def get(self, task_name: str, block: bool = True,
            timeout: Optional[float] = None) -> _GpuLease:
        deadline = (time.time() + timeout) if (timeout is not None) else None
        first = True
        while True:
            lease_holder: List[Optional[_GpuLease]] = []

            def _take(state, _h=lease_holder):
                _h.append(self._try_acquire(state, task_name))

            self._with_lock(_take)
            lease = lease_holder[0]
            if lease is not None:
                self._held.append(int(lease.slot_id))
                return lease
            if not block:
                raise queue.Empty()
            if deadline is not None and time.time() >= deadline:
                raise queue.Empty()
            if first:
                logger.info(
                    "Shared GPU pool: GPU %d has all %d slots busy; waiting...",
                    self._gpu_id, self._slots,
                )
                first = False
            time.sleep(self.POLL_INTERVAL)

    def put(self, lease: _GpuLease) -> None:
        if lease.slot_id is None:
            return
        my_pid = os.getpid()
        slot_id = int(lease.slot_id)

        def _release(state):
            entry = state.get("shared_gpus", {}).get(str(self._gpu_id))
            if not entry:
                return
            slot = entry.get("slots", {}).get(str(slot_id))
            if slot and slot.get("holder_pid") == my_pid:
                self._clear_slot(slot)

        self._with_lock(_release)
        try:
            self._held.remove(slot_id)
        except ValueError:
            pass

    def release_all(self) -> None:
        for slot_id in list(self._held):
            try:
                self.put(
                    _GpuLease(
                        gpu_id=self._gpu_id,
                        kind="shared",
                        task_name="<release_all>",
                        slot_id=slot_id,
                    )
                )
            except Exception:
                pass


class _TaskGpuAllocator:
    """Route tasks to the normal exclusive pool or the shared slot pool."""

    def __init__(self, normal_pool: Optional[Any],
                 shared_pool: Optional[_FileSharedGpuSlotPool],
                 shared_tasks: Set[str]) -> None:
        self._normal_pool = normal_pool
        self._shared_pool = shared_pool
        self._shared_tasks = shared_tasks

    def get(self, task_name: str, block: bool = True,
            timeout: Optional[float] = None) -> Optional[_GpuLease]:
        if self._shared_pool is not None and task_name in self._shared_tasks:
            return self._shared_pool.get(task_name, block=block, timeout=timeout)
        if self._normal_pool is None:
            return None
        gid = self._normal_pool.get(block=block, timeout=timeout)
        return _GpuLease(gpu_id=gid, kind="normal", task_name=task_name)

    def put(self, lease: _GpuLease) -> None:
        if lease.kind == "shared":
            if self._shared_pool is not None:
                self._shared_pool.put(lease)
            return
        if self._normal_pool is not None:
            self._normal_pool.put(lease.gpu_id)

    def release_all(self) -> None:
        if self._normal_pool is not None and hasattr(self._normal_pool, "release_all"):
            self._normal_pool.release_all()
        if self._shared_pool is not None:
            self._shared_pool.release_all()


def _monitor_and_kill(
    proc: subprocess.Popen,
    task_name: str,
    container_name: str,
    eval_service_url: str,
    timeout: int,
    poll_interval: int = 60,
    stop_reason: Optional[dict] = None,
    batch_name: Optional[str] = None,
) -> None:
    """Watcher thread: poll /time_remaining every poll_interval seconds; stop the container when remaining <=0 or should_skip is set."""
    host_url = _host_url(eval_service_url)
    while proc.poll() is None:
        time.sleep(poll_interval)
        if proc.poll() is not None:
            break
        try:
            url = f"{host_url}/time_remaining?task_name={urllib.parse.quote(task_name)}"
            if batch_name:
                url += "&batch_name=" + urllib.parse.quote(batch_name)
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            remaining = data.get("remaining_seconds")
            should_skip = data.get("should_skip", False)
            if should_skip:
                consec = data.get("consecutive_failures", "?")
                logger.warning(
                    "[%s] should_skip=True (consecutive_failures=%s), stopping container",
                    task_name, consec,
                )
                if stop_reason is not None:
                    stop_reason["reason"] = "eval_skip"
                    stop_reason["consecutive_failures"] = consec
                subprocess.run(
                    ["docker", "stop", "-t", "10", container_name],
                    capture_output=True, text=True,
                )
                return
            if remaining is not None and remaining <= 0:
                logger.warning(
                    "[%s] time_remaining=%.1f, stopping container",
                    task_name, remaining,
                )
                if stop_reason is not None:
                    stop_reason["reason"] = "timeout"
                subprocess.run(
                    ["docker", "stop", "-t", "10", container_name],
                    capture_output=True, text=True,
                )
                return
        except Exception as e:
            logger.debug("[%s] Monitor poll failed: %s", task_name, e)


def _run_single_task(
    task_name: str,
    data_dir: Path,
    out_dir: Path,
    agent_name: str,
    model: str,
    mode: str,
    eval_service_url: str,
    timeout: int,
    gpu_allocator: Optional[_TaskGpuAllocator] = None,
    tracker: Optional[Any] = None,
    skip_build: bool = False,
    base_image: str = "naturebench-base:v3",
    dockerfile_name: str = "Dockerfile.v3",
    *,
    is_resume: bool = False,
    setup_timeout: int = 14400,
    codex_auth_dir: Optional[Path] = None,
    codex_use_api_key: bool = False,
    proxy_mode: str = "host",
    proxy_container: Optional[str] = None,
    proxy_network: Optional[str] = None,
    proxy_bundle: Optional[Path] = None,
    proxy_http_port: int = 7890,
    proxy_socks_port: int = 7891,
) -> Dict[str, Any]:
    """Run a single task inside a Docker container.

    1. Ensure task Docker image exists (build if needed)
    2. Build agent prompt with eval service URL
    3. Start container with proper mounts
    4. Run agent CLI inside container
    5. Handle timeout
    6. Return result dict

    is_resume=True means the task already has a Claude session and should be
    continued via `claude --resume <sid>` instead of started fresh. The caller
    is responsible for verifying eligibility (sid file + .claude_state dir +
    eval_service still has prior task state) before flipping this flag.
    """
    task_start = time.time()
    gpu_lease: Optional[_GpuLease] = None
    task_root = data_dir / task_name
    task_out_dir = out_dir / task_name
    workspace_dir = task_out_dir / "workspace"
    output_dir = workspace_dir / "output"

    # Create directories
    workspace_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = task_out_dir / f"{agent_name}.jsonl"
    err_path = task_out_dir / f"{agent_name}.err"
    task_codex_state_dir: Optional[Path] = None
    codex_resume_sid: Optional[str] = None
    if agent_name == "codex" and is_resume and codex_use_api_key:
        raise RuntimeError(
            f"[{task_name}] codex resume not supported in api-key mode"
        )
    if agent_name == "codex" and not codex_use_api_key and codex_auth_dir is not None:
        task_codex_state_dir = _prepare_task_codex_state_dir(
            task_out_dir,
            codex_auth_dir,
            reseed=not is_resume,
        )
        if is_resume:
            sid_file = task_out_dir / "codex_session_id.txt"
            if not sid_file.exists():
                raise RuntimeError(
                    f"[{task_name}] resume requested but {sid_file} not found"
                )
            codex_resume_sid = sid_file.read_text(encoding="utf-8").strip()

    # --- Resume bookkeeping ---
    # For Claude we mount <task>/.claude_state into the container's
    # /root/.claude so that the CLI's session jsonl persists across container
    # exits, which is what makes `claude --resume <uuid>` possible later.
    claude_session_id: Optional[str] = None
    claude_state_dir: Optional[Path] = None
    prior_history: List[Dict[str, Any]] = []
    if agent_name == "claude":
        claude_session_id = _setup_session_id(task_out_dir, task_name, is_resume)
        claude_state_dir = task_out_dir / ".claude_state"
        claude_state_dir.mkdir(parents=True, exist_ok=True)
        prior_history = _load_resume_history(task_out_dir) if is_resume else []
    elif agent_name == "codex" and is_resume:
        prior_history = _load_resume_history(task_out_dir)
    # Gemini session/state management (symmetric with claude/codex)
    gemini_session_id: Optional[str] = None
    gemini_state_dir: Optional[Path] = None
    if agent_name == "gemini":
        gemini_session_id = _setup_gemini_session_id(task_out_dir, task_name, is_resume)
        gemini_state_dir = task_out_dir / ".gemini_state"
        gemini_state_dir.mkdir(parents=True, exist_ok=True)
        prior_history = _load_resume_history(task_out_dir) if is_resume else []

    result: Dict[str, Any] = {
        "task_name": task_name,
        "agent": agent_name,
        "model": model,
        "mode": mode,
        "status": "error",
        "duration": 0,
        "returncode": None,
    }
    if claude_session_id:
        result["session_id"] = claude_session_id
    elif codex_resume_sid:
        result["session_id"] = codex_resume_sid
    elif gemini_session_id:
        result["session_id"] = gemini_session_id
    if is_resume:
        result["is_resume_run"] = True

    try:
        # 1. Ensure image
        if skip_build:
            image_tag = base_image
            dockerfile = data_dir / task_name / "environment" / dockerfile_name
            df_spec = _parse_dockerfile(dockerfile)
            logger.info("[%s] Skip-build mode (dockerfile=%s): %d RUN cmds, %d ENV vars, %d COPY entries",
                        task_name, dockerfile_name, len(df_spec.run_commands),
                        len(df_spec.env_vars), len(df_spec.copy_srcs))
        else:
            image_tag = _ensure_task_image(task_name, data_dir, base_image=base_image, dockerfile_name=dockerfile_name)
            df_spec = DockerfileSpec()

        if agent_name == "codex" and not codex_use_api_key and task_codex_state_dir is not None:
            logger.debug("[%s] codex device-auth state ready at %s", task_name, task_codex_state_dir)

        # 2. Build agent prompt
        eval_output_dir = str(output_dir.resolve())  # Host path for eval service
        time_limit_minutes = max(1, timeout // 60)
        task_info = {
            "task_name": task_name,
            "batch_name": out_dir.name,
            "eval_service_url": eval_service_url,
            "eval_output_dir": eval_output_dir,
            "time_limit_minutes": time_limit_minutes,
        }

        from agent import ClaudeAgent, CodexAgent, GeminiAgent
        if agent_name == "claude":
            agent = ClaudeAgent(model_name=model, mode=mode)
            system_prompt = _RESUME_PROMPT_CLAUDE if is_resume else agent.build_system_prompt(task_info)
            agent_cmd = _build_claude_cmd(
                system_prompt, model,
                session_id=claude_session_id,
                resume_session=is_resume,
            )
        elif agent_name == "codex":
            agent = CodexAgent(model_name=model, mode=mode)
            system_prompt = _RESUME_PROMPT_CODEX if is_resume else agent.build_system_prompt(task_info)
            agent_cmd = _build_codex_cmd(
                system_prompt,
                model,
                resume_session_id=codex_resume_sid,
                use_api_key=codex_use_api_key,
                api_base_url=os.environ.get("OPENAI_BASE_URL"),
            )
            if task_codex_state_dir is not None:
                agent_cmd = _codex_exec_cmd(agent_cmd)
        elif agent_name == "gemini":
            agent = GeminiAgent(model_name=model, mode=mode)
            system_prompt = _RESUME_PROMPT_GEMINI if is_resume else agent.build_system_prompt(task_info)
            agent_cmd = _build_gemini_cmd(
                system_prompt, model,
                session_id=gemini_session_id,
                resume_session=is_resume,
            )
        else:
            raise ValueError(f"Unsupported agent for Docker mode: {agent_name}")

        # 3. Construct docker run command
        # Container name: include batch (out_dir.name) so multiple solve.py
        # processes (e.g. one per model) can run the same task in parallel
        # without colliding on `naturebench-solve-<task>`. Docker enforces a 253
        # char limit on container names — we hash the (batch,task) tuple if it
        # would exceed, keeping the prefix readable.
        _raw_name = f"naturebench-solve-{out_dir.name}-{task_name}"
        if len(_raw_name) <= 253:
            container_name = _raw_name
        else:
            import hashlib as _hl
            _digest = _hl.sha1(f"{out_dir.name}:{task_name}".encode()).hexdigest()[:12]
            container_name = f"naturebench-solve-{task_name[:200]}-{_digest}"
        _remove_container(container_name)  # Clean up any stale container

        host_task_problem = str((task_root / "problem").resolve())
        host_workspace = str(workspace_dir.resolve())

        docker_cmd: List[str] = [
            "docker", "run",
            "--name", container_name,
        ]

        # GPU support: acquire one GPU. With cross-process pool (--gpu-pool-file)
        # this blocks until a GPU is freed by either this process or any peer
        # solve.py instance sharing the same pool. Without --gpu-pool-file the
        # behavior is the legacy in-memory queue (also blocking).
        if gpu_allocator is not None:
            try:
                gpu_lease = gpu_allocator.get(task_name, block=True)
                if gpu_lease is not None:
                    docker_cmd.extend(["--gpus", f"device={gpu_lease.gpu_id}"])
                    if gpu_lease.kind == "shared":
                        logger.info(
                            "[%s] Acquired shared GPU %d slot %d",
                            task_name, gpu_lease.gpu_id, gpu_lease.slot_id,
                        )
                    else:
                        logger.info(
                            "[%s] Acquired GPU %d",
                            task_name, gpu_lease.gpu_id,
                        )
            except queue.Empty:
                logger.info("[%s] No GPU available, running CPU-only", task_name)
                gpu_lease = None

        if proxy_mode == "sidecar":
            if not proxy_network:
                raise ValueError("proxy_network is required when proxy_mode=sidecar")
            docker_cmd.extend(["--network", proxy_network])

        # Network: allow container to reach host eval service
        if platform.system() == "Linux":
            docker_cmd.extend(["--add-host=host.docker.internal:host-gateway"])
        # macOS Docker Desktop provides host.docker.internal automatically

        # Mounts
        docker_cmd.extend([
            "-v", f"{host_task_problem}:/task/problem:ro",
            "-v", f"{host_workspace}:/workspace",
        ])

        # Embedded clash: mount the bundle so the in-container setup phase can
        # launch clash on 127.0.0.1:7890/7891 before dependency setup and the
        # agent start.
        if proxy_mode == "embedded":
            if not proxy_bundle or not proxy_bundle.is_dir():
                raise ValueError(
                    f"proxy_mode=embedded requires a clash bundle dir; got {proxy_bundle}"
                )
            docker_cmd.extend([
                "-v", f"{str(proxy_bundle.resolve())}:/clash-bundle:ro",
            ])

        # Persist Claude Code session jsonl outside the container so that
        # `--resume <sid>` can pick it up later. CLI default home is
        # `/root/.claude`. Other agents (codex/gemini) ignore this mount.
        if agent_name == "claude" and claude_state_dir is not None:
            docker_cmd.extend([
                "-v", f"{str(claude_state_dir.resolve())}:/root/.claude",
            ])

        # Gemini CLI stores session state in ~/.gemini. Mount .gemini_state
        # so sessions persist across container restarts for resume.
        if agent_name == "gemini" and gemini_state_dir is not None:
            docker_cmd.extend([
                "-v", f"{str(gemini_state_dir.resolve())}:/root/.gemini",
            ])

        # Gemini: mount the no-web policy file into the container.
        if agent_name == "gemini":
            _policy_src = Path(__file__).parent / ".gemini_policies" / "no-web.toml"
            if _policy_src.exists():
                docker_cmd.extend([
                    "-v", f"{str(_policy_src.resolve())}:/etc/naturebench/no-web.toml:ro",
                ])

        # Reproduce mode: mount paper PDF and paper markdown
        if mode == "reproduce":
            # Mount paper PDF (named {task_name}.pdf at task_root)
            paper_pdfs = list(task_root.glob("*.pdf"))
            if paper_pdfs:
                docker_cmd.extend([
                    "-v", f"{str(paper_pdfs[0].resolve())}:/task/paper.pdf:ro",
                ])
            # Mount preprocessed text.md as paper.md
            paper_md = task_root / "preprocessed" / "text.md"
            if paper_md.exists():
                docker_cmd.extend([
                    "-v", f"{str(paper_md.resolve())}:/task/paper.md:ro",
                ])

        # Environment variables
        docker_cmd.extend([
            "-e", f"EVAL_SERVICE_URL={eval_service_url}",
            "-e", "DATA_DIR=/task/problem/data",
            "-e", "OUTPUT_DIR=/workspace/output",
            "-e", "NVIDIA_DISABLE_REQUIRE=1",
            "-e", "NONINTERACTIVE=1",
            "-e", "CI=1",
        ])
        if proxy_mode == "host":
            docker_cmd.extend(_host_proxy_env_args())

        # Pass through API keys and optional provider base URLs only when the
        # user has explicitly provided them in the host environment. Do not
        # bake private provider defaults into the public release.
        for key in (
            "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_API_BASE", "ANTHROPIC_MODEL",
            "OPENAI_API_KEY", "OPENAI_BASE_URL",
            "GEMINI_API_KEY", "GOOGLE_GEMINI_BASE_URL",
        ):
            val = os.environ.get(key)
            if val:
                # For Codex, only pass OPENAI_API_KEY / OPENAI_BASE_URL if the
                # selected auth mode is API-key mode. In device-auth mode the
                # container reads official login state mounted via HOME.
                if agent_name == "codex" and key in ("OPENAI_API_KEY", "OPENAI_BASE_URL"):
                    if codex_use_api_key and os.environ.get(key):
                        docker_cmd.extend(["-e", f"{key}={val}"])
                else:
                    docker_cmd.extend(["-e", f"{key}={val}"])

        # Codex official auth persistence: mount host auth dir into the
        # container's HOME/.codex so `codex login --device-auth` can be reused.
        if agent_name == "codex" and not codex_use_api_key and task_codex_state_dir is not None:
            docker_cmd.extend(_codex_auth_mount_args(task_codex_state_dir))

        if proxy_mode == "sidecar":
            proxy_host = proxy_container
            docker_cmd.extend(
                _proxy_env_args(
                    proxy_host,
                    proxy_http_port,
                    proxy_socks_port,
                )
            )
        elif proxy_mode == "embedded":
            docker_cmd.extend(
                _proxy_env_args(
                    "127.0.0.1",
                    proxy_http_port,
                    proxy_socks_port,
                )
            )
        # Skip-build: inject ENV vars from Dockerfile
        # Vars referencing other vars (e.g. ${PATH}) must be set inside the
        # container shell, not via docker -e (which doesn't expand them).
        env_setup_cmds: List[str] = []
        if skip_build and df_spec.env_vars:
            for k, v in df_spec.env_vars.items():
                if "${" in v or "$(" in v:
                    # Needs shell expansion — set inside container
                    env_setup_cmds.append(f'export {k}="{v}"')
                else:
                    docker_cmd.extend(["-e", f"{k}={v}"])

        # Skip-build: handle COPY sources from task Dockerfile
        # Build context is the environment/ directory. If the file isn't found
        # there, fall back to the task root (task packages sometimes store
        # binaries in evaluation/ which is a sibling of environment/).
        copy_setup_cmds: List[str] = []
        if skip_build and df_spec.copy_srcs:
            env_dir = data_dir / task_name / "environment"
            task_root_dir = data_dir / task_name
            for src, dest in df_spec.copy_srcs:
                # Try build context first, then task root
                candidate = env_dir / src
                if not candidate.exists() or candidate.is_dir():
                    candidate = task_root_dir / src
                if not candidate.exists():
                    logger.warning("[%s] COPY source not found: %s", task_name, src)
                    continue
                host_src = str(candidate.resolve())
                stage_name = Path(src).name
                stage_path = f"/tmp/_copy_stage/{stage_name}"
                docker_cmd.extend(["-v", f"{host_src}:{stage_path}:ro"])
                copy_setup_cmds.append(f"cp {shlex.quote(stage_path)} {shlex.quote(dest)}")

        # Image
        docker_cmd.append(image_tag)

        # Determine setup commands (skip-build mode)
        run_cmds = df_spec.run_commands if skip_build else []
        # Add --no-build-isolation to pip install commands so they can see
        # packages already installed in the base image (e.g. torch).
        if skip_build:
            patched = []
            for cmd in run_cmds:
                if "pip install" in cmd and "--no-build-isolation" not in cmd:
                    cmd = cmd.replace("pip install", "pip install --no-build-isolation", 1)
                patched.append(cmd)
            run_cmds = patched
        all_setup = env_setup_cmds + copy_setup_cmds + run_cmds
        # Embedded clash must come up BEFORE any user setup that might need
        # outbound network (apt/pip via proxy etc.), and definitely before the
        # agent itself.
        if proxy_mode == "embedded":
            all_setup = _embedded_clash_setup_cmds() + all_setup

        logger.info("[%s] Starting container %s with image %s", task_name, container_name, image_tag)

        if all_setup:
            # === Two-phase launch: setup first, then start timer, then agent ===
            # Phase 1: Start container detached with a long sleep so it
            # outlives both setup and agent. Lifetime budget:
            #   setup_timeout + timeout + 600 (cleanup margin)
            container_lifetime = setup_timeout + timeout + 600  # Ensure the container lifetime covers the setup, agent run, and evaluation durations
            run_detach = docker_cmd[:2] + ["-d"] + docker_cmd[2:]
            run_detach.extend(["/bin/bash", "-c", f"sleep {container_lifetime}"])
            proc_d = subprocess.run(run_detach, capture_output=True, text=True)
            if proc_d.returncode != 0:
                raise RuntimeError(
                    f"Failed to start container: {proc_d.stderr[-500:]}"
                )
            logger.info(
                "[%s] Container started (lifetime=%ds), running setup (timeout=%ds)...",
                task_name, container_lifetime, setup_timeout,
            )

            # Phase 2: Run setup inside the container
            setup_script = " && ".join(all_setup)
            setup_exec = [
                "docker", "exec", container_name,
                "/bin/bash", "-c", setup_script,
            ]
            proc_setup = subprocess.run(
                setup_exec, capture_output=True, text=True,
                encoding="utf-8", timeout=setup_timeout,
            )
            if proc_setup.returncode != 0:
                raise RuntimeError(
                    f"Setup failed (exit {proc_setup.returncode}): "
                    f"{proc_setup.stderr[-500:]}"
                )
            logger.info("[%s] Setup complete, launching agent...", task_name)

            # Phase 3: Set timer NOW (after setup, before agent)
            if tracker:
                state = tracker.get_task(task_name)
                if state:
                    state.start_time = time.time()
            # Notify external eval service so /time_remaining works.
            # Resume runs continue the existing timer; fresh runs (re)start it.
            if is_resume:
                _notify_timer_resume(eval_service_url, task_name, batch_name=out_dir.name)
            else:
                _notify_timer_start_from_url(eval_service_url, task_name, batch_name=out_dir.name)

            # Phase 4: Run agent inside the container (with timeout via monitor thread)
            agent_cmd_str = " ".join(shlex.quote(a) for a in agent_cmd)
            agent_exec = [
                "docker", "exec", "-w", "/workspace", container_name,
                "/bin/bash", "-c", agent_cmd_str,
            ]
            with open(log_path, "w", encoding="utf-8") as f_out, \
                 open(err_path, "w", encoding="utf-8") as f_err:
                proc = subprocess.Popen(
                    agent_exec, stdin=subprocess.DEVNULL,
                    stdout=f_out, stderr=f_err,
                    text=True, encoding="utf-8",
                )
                stop_reason: dict = {}
                monitor = threading.Thread(
                    target=_monitor_and_kill,
                    args=(proc, task_name, container_name,
                          eval_service_url, timeout),
                    kwargs={"stop_reason": stop_reason, "batch_name": out_dir.name},
                    daemon=True,
                )
                monitor.start()
                try:
                    proc.wait(timeout=timeout * 2)
                except subprocess.TimeoutExpired:
                    logger.warning("[%s] Safety timeout (%ds), stopping", task_name, timeout * 2)
                    stop_reason["reason"] = "timeout"
                    subprocess.run(
                        ["docker", "stop", "-t", "10", container_name],
                        capture_output=True, text=True,
                    )
                    proc.wait(timeout=30)

                if stop_reason.get("reason") == "eval_skip":
                    result["status"] = "eval_skip"
                    result["returncode"] = -2
                    logger.warning(
                        "[%s] Skipped: consecutive eval failures (%s)",
                        task_name, stop_reason.get("consecutive_failures"),
                    )
                elif stop_reason.get("reason") == "timeout":
                    result["status"] = "timeout"
                    result["returncode"] = -1
                elif proc.returncode == 0:
                    result["status"] = "success"
                    result["returncode"] = 0
                elif proc.returncode is None or proc.returncode in (-9, 137, 143):
                    result["status"] = "killed"
                    result["returncode"] = proc.returncode
                    logger.warning(
                        "[%s] Process killed externally (returncode=%s), not a timeout",
                        task_name, proc.returncode,
                    )
                else:
                    result["status"] = "agent_error"
                    result["returncode"] = proc.returncode
                    logger.warning(
                        "[%s] Agent exited with code %d", task_name, proc.returncode
                    )

        else:
            # === Single-phase launch: no setup needed ===
            docker_cmd.extend(agent_cmd)

            # Set timer (no setup delay)
            if tracker:
                state = tracker.get_task(task_name)
                if state:
                    state.start_time = time.time()
            # Notify external eval service. Resume runs continue the existing
            # timer; fresh runs (re)start it.
            if is_resume:
                _notify_timer_resume(eval_service_url, task_name, batch_name=out_dir.name)
            else:
                _notify_timer_start_from_url(eval_service_url, task_name, batch_name=out_dir.name)

            with open(log_path, "w", encoding="utf-8") as f_out, \
                 open(err_path, "w", encoding="utf-8") as f_err:
                proc = subprocess.Popen(
                    docker_cmd, stdin=subprocess.DEVNULL,
                    stdout=f_out, stderr=f_err,
                    text=True, encoding="utf-8",
                )
                stop_reason: dict = {}
                monitor = threading.Thread(
                    target=_monitor_and_kill,
                    args=(proc, task_name, container_name,
                          eval_service_url, timeout),
                    kwargs={"stop_reason": stop_reason, "batch_name": out_dir.name},
                    daemon=True,
                )
                monitor.start()
                try:
                    proc.wait(timeout=timeout * 2)
                except subprocess.TimeoutExpired:
                    logger.warning("[%s] Safety timeout (%ds), stopping", task_name, timeout * 2)
                    stop_reason["reason"] = "timeout"
                    subprocess.run(
                        ["docker", "stop", "-t", "10", container_name],
                        capture_output=True, text=True,
                    )
                    proc.wait(timeout=30)

                if stop_reason.get("reason") == "eval_skip":
                    result["status"] = "eval_skip"
                    result["returncode"] = -2
                    logger.warning(
                        "[%s] Skipped: consecutive eval failures (%s)",
                        task_name, stop_reason.get("consecutive_failures"),
                    )
                elif stop_reason.get("reason") == "timeout":
                    result["status"] = "timeout"
                    result["returncode"] = -1
                elif proc.returncode == 0:
                    result["status"] = "success"
                    result["returncode"] = 0
                elif proc.returncode is None or proc.returncode in (-9, 137, 143):
                    result["status"] = "killed"
                    result["returncode"] = proc.returncode
                    logger.warning(
                        "[%s] Process killed externally (returncode=%s), not a timeout",
                        task_name, proc.returncode,
                    )
                else:
                    result["status"] = "agent_error"
                    result["returncode"] = proc.returncode
                    logger.warning(
                        "[%s] Agent exited with code %d", task_name, proc.returncode
                    )

        # Clean up container (docker run without --rm, we clean up manually)
        _remove_container(container_name)

        if agent_name == "codex" and task_codex_state_dir is not None:
            sid = _capture_codex_session_id(
                task_codex_state_dir,
                since_mtime=task_start,
            )
            if sid:
                (task_out_dir / "codex_session_id.txt").write_text(sid, encoding="utf-8")
                result["session_id"] = sid
            elif not is_resume:
                logger.warning(
                    "[%s] could not capture codex session id; future resume will be ineligible",
                    task_name,
                )
                result["codex_session_capture_failed"] = True

        # Gemini fresh runs let the CLI assign its own session UUID; capture
        # it from the stream-json init event so future resumes can find it.
        if agent_name == "gemini" and not is_resume:
            sid = _capture_gemini_session_id(log_path)
            if sid:
                (task_out_dir / "gemini_session_id.txt").write_text(sid, encoding="utf-8")
                result["session_id"] = sid
                logger.info("[%s] Gemini session ID captured: %s", task_name, sid)
            else:
                logger.warning(
                    "[%s] could not capture gemini session id; future resume will be ineligible",
                    task_name,
                )
                result["gemini_session_capture_failed"] = True

    except Exception as exc:
        logger.error("[%s] Error: %s", task_name, exc, exc_info=True)
        result["status"] = "error"
        result["message"] = str(exc)

    finally:
        # Always release GPU back to pool
        if gpu_lease is not None and gpu_allocator is not None:
            gpu_allocator.put(gpu_lease)
            if gpu_lease.kind == "shared":
                logger.info(
                    "[%s] Released shared GPU %d slot %d",
                    task_name, gpu_lease.gpu_id, gpu_lease.slot_id,
                )
            else:
                logger.info("[%s] Released GPU %d", task_name, gpu_lease.gpu_id)

    # Wait for any in-flight evaluation to finish before capturing the final
    # score and pausing the task timer. In external-eval mode the local tracker
    # does not reflect the remote eval_service's active_evals, so always poll
    # the service directly before POST /pause_timer.
    _wait_eval_drain(
        eval_service_url,
        task_name,
        batch_name=out_dir.name,
        poll_interval=2.0,
    )

    # Pause the eval_service timer for this task. Until/unless someone resumes
    # this task later, the wall-clock between now and the next /resume_timer
    # call must NOT count against the agent's solve budget. Eval service treats
    # the call as idempotent: if active_evals>0 (eval still in flight) or the
    # timer is already paused, the call is rejected/no-op safely. We do not
    # gate this on the per-task status because the eval-analysis taxonomy
    # allows even `success` cases (D/F) to be resumed later by user choice.
    _notify_timer_pause(eval_service_url, task_name, batch_name=out_dir.name)

    this_run_duration = time.time() - task_start

    # Build cumulative resume_history (this run + any prior runs).
    new_history_entry: Dict[str, Any] = {
        "run_idx": len(prior_history),
        "is_resume_run": bool(is_resume),
        "status": result["status"],
        "returncode": result.get("returncode"),
        "duration": this_run_duration,
        "started_at": datetime.fromtimestamp(task_start, tz=timezone.utc).isoformat(),
    }
    full_history = prior_history + [new_history_entry]
    result["resume_history"] = full_history

    # Cumulative duration: sum across all runs (matches user-requested semantics
    # so that downstream stats reflect total agent wall-clock on this task).
    result["duration"] = sum((entry.get("duration") or 0.0) for entry in full_history)

    # Save result.json for this task
    result_path = task_out_dir / "result.json"
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    return result


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def _build_summary(
    results: List[Dict[str, Any]],
    score_tracker: ScoreTracker,
    total_duration: float,
) -> Dict[str, Any]:
    """Build a summary combining task results with eval service scores."""
    all_scores = score_tracker.all_results()

    # Merge scores into results (don't overwrite values already set by external fetch)
    for r in results:
        task_name = r["task_name"]
        score_info = all_scores.get(task_name, {})
        if r.get("best_attempt") is None:
            r["best_attempt"] = score_info.get("best_attempt")
        if r.get("best_aggregate_improvement") is None:
            r["best_aggregate_improvement"] = score_info.get("best_aggregate_improvement")
        if not r.get("best_per_instance_improvement"):
            r["best_per_instance_improvement"] = score_info.get("best_per_instance_improvement", {})
        if not r.get("best_raw_scores"):
            r["best_raw_scores"] = score_info.get("best_raw_scores", {})
        if not r.get("total_attempts"):
            r["total_attempts"] = score_info.get("total_attempts", 0)

    scored = [r for r in results if r.get("best_aggregate_improvement") is not None]
    successes = sum(1 for r in results if r["status"] == "success")
    if scored:
        avg_agg = sum(r["best_aggregate_improvement"] for r in scored) / len(scored)
    else:
        avg_agg = None

    return {
        "total_tasks": len(results),
        "successes": successes,
        "scored_tasks": len(scored),
        "average_best_aggregate_improvement": avg_agg,
        "total_duration": total_duration,
        "average_duration": total_duration / len(results) if results else 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }


# ---------------------------------------------------------------------------
# Multi-env eval service helpers
# ---------------------------------------------------------------------------

def _load_eval_env_mapping(mapping_path: str) -> Tuple[Dict[str, int], int]:
    """Load eval_env_mapping.json and build task_name → port mapping.

    Returns:
        (task_port_map, default_port): task_port_map maps specific tasks
        to non-default ports; default_port is used for all other tasks.
    """
    with open(mapping_path, encoding="utf-8") as f:
        mapping = json.load(f)

    envs = mapping["environments"]
    default_env = mapping.get("default_env", "main")
    default_port = envs[default_env]["port"]

    task_port_map: Dict[str, int] = {}
    for task_name, env_name in mapping.get("task_routing", {}).items():
        if env_name in envs:
            task_port_map[task_name] = envs[env_name]["port"]

    return task_port_map, default_port


def _register_task_with_service(
    port: int, task_name: str, data_dir: str, timeout: int,
    out_dir: Optional[str] = None,
    batch_name: Optional[str] = None,
    force: bool = False,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Register a task with an external eval service via POST /register.

    Returns:
        (status, payload):
          status ∈ {"ok", "incomplete_metadata", "error"}
          payload = parsed JSON response (may be None on network failure)
    """
    url = f"http://localhost:{port}/register"
    payload_dict = {
        "task_name": task_name,
        "data_dir": data_dir,
        "timeout": timeout,
    }
    if out_dir:
        payload_dict["out_dir"] = out_dir
    if batch_name:
        payload_dict["batch_name"] = batch_name
    if force:
        payload_dict["force"] = True
    payload = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return (result.get("status", "error"), result)
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8", errors="replace"))
            return (body.get("status", "error"), body)
        except Exception:
            return ("error", None)
    except (urllib.error.URLError, OSError) as e:
        logger.error("Failed to register %s with eval service at port %d: %s",
                     task_name, port, e)
        return ("error", None)


def _fetch_score_from_service(port: int, task_name: str,
                              batch_name: Optional[str] = None) -> Dict[str, Any]:
    """Fetch best score for a task from an external eval service."""
    qs = f"task_name={task_name}"
    if batch_name:
        qs += f"&batch_name={batch_name}"
    url = f"http://localhost:{port}/best_score?{qs}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError) as e:
        logger.warning("Failed to fetch score for %s from port %d: %s",
                       task_name, port, e)
        return {}


def _notify_timer_start(port: int, task_name: str,
                        batch_name: Optional[str] = None) -> None:
    """Notify external eval service that a task's timer has started."""
    url = f"http://localhost:{port}/start_timer"
    body = {"task_name": task_name}
    if batch_name:
        body["batch_name"] = batch_name
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except (urllib.error.URLError, OSError) as e:
        logger.warning("Failed to notify timer start for %s on port %d: %s",
                       task_name, port, e)


def _notify_timer_start_from_url(eval_service_url: str, task_name: str,
                                  batch_name: Optional[str] = None) -> None:
    """Extract port from eval_service_url and notify timer start."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(eval_service_url)
        port = parsed.port or 8321
        _notify_timer_start(port, task_name, batch_name=batch_name)
    except Exception as e:
        logger.warning("Failed to parse eval URL for timer notification: %s", e)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Drive an agent to solve NatureBench tasks inside Docker containers.",
    )
    parser.add_argument(
        "--config", default=None,
        help="Optional YAML config file. Values are read from the 'solve' section.",
    )
    parser.add_argument(
        "--task-set", default=None,
        help="TXT file listing task names (one per line or JSON lines).",
    )
    parser.add_argument(
        "--data-dir", default=None,
        help="Root directory containing task packages.",
    )
    parser.add_argument(
        "--out-dir", default=None,
        help="Output directory for results.",
    )
    parser.add_argument(
        "--agent", default=None, choices=["claude", "codex", "gemini"],
        help="Agent to use (claude, codex, or gemini).",
    )
    parser.add_argument(
        "--model", default=None,
        help="Model name for the agent.",
    )
    parser.add_argument(
        "--mode", default=None, choices=["base", "reproduce"],
        help="Solve mode: 'base' for the public benchmark protocol or 'reproduce' with paper materials.",
    )
    parser.add_argument(
        "--timeout", type=int, default=None,
        help="Per-task agent solve budget in seconds (default: 14400 = 4h). This is "
             "the timer registered with eval_service; setup time is excluded.",
    )
    parser.add_argument(
        "--setup-timeout", type=int, default=None,
        help="Per-task setup-phase upper bound in seconds (default: 14400 = 4 h). "
             "Caps the docker exec time spent on pip install / dependency "
             "preparation BEFORE the agent timer starts. Distinct from "
             "--timeout so agent solve budget isn't consumed by setup.",
    )
    parser.add_argument(
        "--max-workers", type=int, default=None,
        help="Max parallel tasks (default: 1).",
    )
    parser.add_argument(
        "--eval-port", type=int, default=None,
        help="Evaluation service port (default: 8321).",
    )
    parser.add_argument(
        "--gpu-devices", default=None,
        help="Comma-separated GPU device IDs to use (e.g. '0,1,4,5,8,9'). "
             "Each container gets one GPU. Concurrency is limited to the number "
             "of GPUs specified. Omit to run without GPU.",
    )
    parser.add_argument(
        "--skip-build", action="store_true", default=None,
        help="Skip per-task image build. Use base image and install "
             "task dependencies at container startup via pip install.",
    )
    parser.add_argument(
        "--skip-judge", action="store_true", default=False,
        help="Skip post-hoc LLM judge stage. Useful for offline reruns; "
             "judge requires JUDGE_API_KEY or ANTHROPIC_API_KEY.",
    )
    parser.add_argument(
        "--base-image", default="naturebench-base:v3",
        help="Base Docker image to use in skip-build mode (default: naturebench-base:v3).",
    )
    parser.add_argument(
        "--dockerfile-name", default="Dockerfile.v3",
        help="Dockerfile file name inside each task's environment/ dir to parse for setup commands (default: Dockerfile.v3).",
    )
    parser.add_argument(
        "--eval-env-mapping", default=None,
        help="Path to eval_env_mapping.json for multi-environment eval service routing. "
             "When provided, solve.py will NOT start an internal eval service; "
             "external services must already be running on the specified ports.",
    )
    parser.add_argument(
        "--proxy-mode", default=None, choices=["host", "sidecar", "embedded", "none"],
        help="Network proxy mode for any agent. 'host' passes host HTTP(S)/ALL/NO_PROXY "
             "environment variables into task containers; 'embedded' mounts a clash "
             "bundle and starts it inside each task container; 'sidecar' uses a shared "
             "proxy container on a Docker network; 'none' passes no proxy variables. "
             "Defaults to 'embedded' for Codex and 'host' for Claude/Gemini.",
    )
    parser.add_argument(
        "--proxy-bundle", default=None,
        help="Path to a clash/mihomo bundle for --proxy-mode=embedded. If omitted "
             "and embedded mode is selected, solve.py looks for ./.clash-bundle.",
    )
    parser.add_argument(
        "--proxy-container", default=None,
        help="Proxy container name for --proxy-mode=sidecar.",
    )
    parser.add_argument(
        "--proxy-network", default=None,
        help="Docker network shared by task containers and the proxy container for "
             "--proxy-mode=sidecar.",
    )
    parser.add_argument(
        "--proxy-http-port", type=int, default=None,
        help="HTTP proxy port for embedded/sidecar proxy mode. Default: 7890.",
    )
    parser.add_argument(
        "--proxy-socks-port", type=int, default=None,
        help="SOCKS proxy port for embedded/sidecar proxy mode. Default: 7891.",
    )
    parser.add_argument(
        "--codex-auth-dir", default=None,
        help="For Codex device-auth runs, reuse this host directory as the "
             "persistent Codex login state. If omitted, solve.py reuses the "
             "host's ~/.codex login state.",
    )
    parser.add_argument(
        "--codex-auth-mode", default="device-auth", choices=["api-key", "device-auth"],
        help="Codex authentication mode. 'device-auth' uses the mounted "
             "~/.codex login state. 'api-key' requires OPENAI_API_KEY and "
             "optionally OPENAI_BASE_URL on the host.",
    )
    parser.add_argument(
        "--resume-tasks", nargs="*", default=[],
        help="Subset of tasks (by task_name) to run with `claude --resume <sid>` "
             "instead of a fresh session. Each must already have "
             "claude_session_id.txt and .claude_state/ from a prior run.",
    )
    parser.add_argument(
        "--resume-task-file", default=None,
        help="Path to a TXT file listing tasks to resume (one per line, "
             "merged with --resume-tasks).",
    )
    parser.add_argument(
        "--resume-only", action="store_true", default=False,
        help="Only execute the tasks listed in --resume-tasks/--resume-task-file; "
             "skip everything else in --task-set.",
    )
    parser.add_argument(
        "--force-fresh", nargs="*", default=[],
        help="Task names to forcibly run from scratch even if their "
             "task_out_dir already contains a previous result. Existing state "
             "(result.json, submissions.jsonl, .claude_state, etc.) is moved "
             "to _force_fresh_archive_<ts>/ — nothing is deleted. Without this "
             "flag, encountering a prior result.json on a non-resume task is "
             "an error (use --resume-tasks or --force-fresh to choose).",
    )
    parser.add_argument(
        "--gpu-pool-file", default=None,
        help="Path to a JSON file used as a cross-process GPU pool. When set, "
             "multiple solve.py instances (e.g. one per model) coordinate GPU "
             "allocation through fcntl-locked reads/writes of this file: a "
             "task launching on a busy GPU waits until that GPU is freed by "
             "any participant. Without this flag the GPU pool stays per-"
             "process (legacy in-memory queue.Queue). Recommended:"
             "/tmp/naturebench_gpu_pool.json",
    )
    parser.add_argument(
        "--shared-gpu-task-file", default=None,
        help="TXT/JSONL file listing tasks that should use the shared GPU slot "
             "pool instead of the normal exclusive GPU pool.",
    )
    parser.add_argument(
        "--shared-gpu-device", type=int, default=None,
        help="Physical GPU id to share among tasks listed in "
             "--shared-gpu-task-file. It may also appear in --gpu-devices, "
             "but that double-books the physical GPU and can overload it.",
    )
    parser.add_argument(
        "--shared-gpu-slots", type=int, default=5,
        help="Maximum number of shared-task containers allowed on "
             "--shared-gpu-device across all solve.py processes. Default: 5.",
    )
    parser.add_argument(
        "--shared-gpu-pool-file", default=None,
        help="Path to the fcntl-locked JSON state file for the shared GPU slot "
             "pool. Required when shared GPU scheduling is enabled.",
    )
    parser.add_argument(
        "--gpu-skip-busy-mb", type=int, default=2000,
        help="When using --gpu-pool-file, treat a GPU as unavailable if its "
             "currently used memory exceeds this many MB (probed via "
             "nvidia-smi at acquire time). Catches external processes "
             "(other users, other docker containers) holding the GPU even "
             "though our pool file thinks it's free. Set to 0 to disable. "
             "Default: 2000.",
    )
    parser.add_argument(
        "--gpu-skip-busy-util", type=int, default=80,
        help="Companion to --gpu-skip-busy-mb: also skip a GPU if its "
             "utilization (percent) exceeds this. Default: 80.",
    )

    args = parser.parse_args()

    # Load config and merge with CLI args
    config_data = load_yaml_config(args.config)
    args = merge_args_with_config(parser, args, config_data, section="solve")

    # Resolve defaults
    task_file = Path(args.task_set).resolve()
    data_dir = Path(args.data_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    agent_name = args.agent or "claude"
    model = args.model
    if not model:
        raise ValueError("Model name is required. Pass --model.")
    mode = args.mode or "base"
    if mode not in {"base", "reproduce"}:
        raise ValueError(f"Unsupported --mode for the public release: {mode!r}. Use 'base' or 'reproduce'.")
    timeout = args.timeout or 14400
    setup_timeout = getattr(args, "setup_timeout", None) or 14400
    max_workers = args.max_workers or 1
    skip_build = bool(getattr(args, "skip_build", False))
    skip_judge = bool(getattr(args, "skip_judge", False))
    base_image = getattr(args, "base_image", "naturebench-base:v3")
    dockerfile_name = getattr(args, "dockerfile_name", "Dockerfile.v3")

    # GPU pool: in-memory single-process or cross-process file-locked.
    gpu_devices_str = getattr(args, "gpu_devices", None)
    gpu_pool_file_str = getattr(args, "gpu_pool_file", None)
    gpu_skip_busy_mb = int(getattr(args, "gpu_skip_busy_mb", 2000) or 0)
    gpu_skip_busy_util = int(getattr(args, "gpu_skip_busy_util", 80) or 100)
    shared_gpu_task_file_str = getattr(args, "shared_gpu_task_file", None)
    shared_gpu_device = getattr(args, "shared_gpu_device", None)
    shared_gpu_slots = int(getattr(args, "shared_gpu_slots", 5) or 5)
    shared_gpu_pool_file_str = getattr(args, "shared_gpu_pool_file", None)
    gpu_pool = None
    gpu_ids: List[int] = []
    shared_gpu_tasks: Set[str] = set()
    shared_gpu_pool = None

    shared_gpu_enabled = any(
        x is not None for x in (
            shared_gpu_task_file_str,
            shared_gpu_device,
            shared_gpu_pool_file_str,
        )
    )
    if shared_gpu_enabled:
        missing = []
        if not shared_gpu_task_file_str:
            missing.append("--shared-gpu-task-file")
        if shared_gpu_device is None:
            missing.append("--shared-gpu-device")
        if not shared_gpu_pool_file_str:
            missing.append("--shared-gpu-pool-file")
        if missing:
            raise ValueError(
                "Shared GPU scheduling requires all of: "
                + ", ".join(missing)
            )
        if shared_gpu_slots <= 0:
            raise ValueError("--shared-gpu-slots must be positive")
        shared_gpu_task_path = Path(shared_gpu_task_file_str).resolve()
        shared_gpu_tasks = set(_read_task_set(shared_gpu_task_path))
        if not shared_gpu_tasks:
            raise ValueError(f"No shared GPU tasks found in {shared_gpu_task_path}")

    if gpu_devices_str:
        gpu_ids = [int(x.strip()) for x in gpu_devices_str.split(",")]
        if shared_gpu_enabled and shared_gpu_device in gpu_ids:
            logger.warning(
                "Shared GPU device %d also appears in exclusive --gpu-devices=%s; "
                "two pools share this physical GPU — make sure shared tasks "
                "actually use little GPU memory, otherwise OOM is possible. "
                "Recommend lowering --gpu-skip-busy-mb to avoid double-booking.",
                shared_gpu_device, gpu_devices_str,
            )
        pool_path = Path(gpu_pool_file_str).resolve() if gpu_pool_file_str else None
        gpu_pool = _build_gpu_pool(gpu_ids, pool_path,
                                   skip_busy_mb=gpu_skip_busy_mb,
                                   skip_busy_util=gpu_skip_busy_util)
        if pool_path is not None:
            logger.info(
                "GPU pool initialized (cross-process via %s): own_devices=%s, "
                "max_workers=%d, skip_busy_mb=%d, skip_busy_util=%d — workers "
                "block until a GPU is free",
                pool_path, gpu_ids, max_workers, gpu_skip_busy_mb, gpu_skip_busy_util,
            )
        else:
            logger.info(
                "GPU pool initialized (in-memory): %s (%d GPUs, "
                "max_workers=%d — workers block until a GPU is free)",
                gpu_ids, len(gpu_ids), max_workers,
            )

    if shared_gpu_enabled:
        shared_pool_path = Path(shared_gpu_pool_file_str).resolve()
        shared_gpu_pool = _FileSharedGpuSlotPool(
            int(shared_gpu_device),
            shared_gpu_slots,
            shared_pool_path,
        )
        logger.info(
            "Shared GPU slot pool initialized: gpu=%d, slots=%d, "
            "tasks=%d, pool_file=%s",
            shared_gpu_device, shared_gpu_slots, len(shared_gpu_tasks),
            shared_pool_path,
        )

    gpu_allocator = None
    if gpu_pool is not None or shared_gpu_pool is not None:
        gpu_allocator = _TaskGpuAllocator(
            gpu_pool,
            shared_gpu_pool,
            shared_gpu_tasks,
        )

    # Eval service config
    eval_svc_config = config_data.get("eval_service", {})
    eval_port = args.eval_port or eval_svc_config.get("port", 8321)
    eval_host = eval_svc_config.get("host", "0.0.0.0")

    # Multi-env mapping (optional)
    eval_env_mapping_path = getattr(args, "eval_env_mapping", None)
    use_external_eval = bool(eval_env_mapping_path)
    task_port_map: Dict[str, int] = {}
    default_eval_port = eval_port

    if use_external_eval:
        task_port_map, default_eval_port = _load_eval_env_mapping(
            eval_env_mapping_path
        )
        logger.info(
            "Loaded eval env mapping from %s: %d task-specific routes, default port=%d",
            eval_env_mapping_path, len(task_port_map), default_eval_port,
        )

    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)

    # Proxy and Codex auth configuration.
    codex_auth_dir: Optional[Path] = None
    proxy_mode_arg = getattr(args, "proxy_mode", None)
    if proxy_mode_arg:
        proxy_mode = proxy_mode_arg
    elif agent_name == "codex":
        proxy_mode = "embedded"
    else:
        proxy_mode = "host"

    proxy_container = getattr(args, "proxy_container", None)
    proxy_network = getattr(args, "proxy_network", None)
    proxy_bundle_arg = getattr(args, "proxy_bundle", None)
    proxy_bundle: Optional[Path] = None
    proxy_http_port = int(getattr(args, "proxy_http_port", None) or 7890)
    proxy_socks_port = int(getattr(args, "proxy_socks_port", None) or 7891)
    codex_auth_dir_arg = getattr(args, "codex_auth_dir", None)
    codex_auth_mode = getattr(args, "codex_auth_mode", "device-auth")
    codex_use_api_key = codex_auth_mode == "api-key"

    if proxy_mode == "sidecar":
        if not proxy_container or not proxy_network:
            raise ValueError(
                "--proxy-mode=sidecar requires --proxy-container and --proxy-network"
            )
        _ensure_clash_proxy_container(proxy_container, proxy_network)
    elif proxy_mode == "embedded":
        if proxy_bundle_arg:
            proxy_bundle = Path(proxy_bundle_arg).expanduser().resolve()
        else:
            proxy_bundle = (Path.cwd() / ".clash-bundle").resolve()
        if not proxy_bundle.is_dir():
            raise RuntimeError(
                f"--proxy-mode=embedded but bundle dir not found: {proxy_bundle}. "
                "Pass --proxy-bundle explicitly or extract a clash bundle there."
            )
        for required in ("clash", "config/config.yaml"):
            if not (proxy_bundle / required).exists():
                raise RuntimeError(
                    f"clash bundle at {proxy_bundle} is missing {required}"
                )

    if agent_name == "codex":
        if codex_use_api_key and not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("Codex auth mode is api-key, but OPENAI_API_KEY is not set")
        if not codex_use_api_key:
            cad = codex_auth_dir_arg
            codex_auth_dir = Path(cad).expanduser().resolve() if cad else (Path.home() / ".codex")
            if not codex_auth_dir.is_dir():
                raise RuntimeError(
                    "Codex auth dir is not a directory. Run `codex login --device-auth` "
                    f"first or pass --codex-auth-dir explicitly: {codex_auth_dir}"
                )
            _probe_codex_login(
                base_image,
                codex_auth_dir,
                proxy_mode=proxy_mode,
                proxy_container=proxy_container,
                proxy_network=proxy_network,
                proxy_bundle=proxy_bundle,
                proxy_http_port=proxy_http_port,
                proxy_socks_port=proxy_socks_port,
            )

    tasks = _read_task_set(task_file)

    # --- Resume selection (manual, per-task) ---
    resume_set: set = set(getattr(args, "resume_tasks", []) or [])
    if agent_name not in ("claude", "codex", "gemini") and resume_set:
        raise ValueError("--resume-tasks is only supported when --agent is claude, codex, or gemini")
    rt_file = getattr(args, "resume_task_file", None)
    if rt_file:
        rtp = Path(rt_file).resolve()
        if rtp.exists():
            for line in rtp.read_text(encoding="utf-8").splitlines():
                t = line.strip()
                if t and not t.startswith("#"):
                    resume_set.add(t)
        else:
            logger.warning("resume task file not found: %s", rtp)
    if agent_name not in ("claude", "codex", "gemini") and resume_set:
        raise ValueError("--resume-tasks/--resume-task-file are only supported when --agent is claude, codex, or gemini")
    resume_only = bool(getattr(args, "resume_only", False))
    force_fresh_set: set = set(getattr(args, "force_fresh", []) or [])

    if resume_only:
        unknown = sorted(resume_set - set(tasks))
        if unknown:
            logger.warning(
                "resume_only mode: %d task(s) not in --task-set, skipped: %s",
                len(unknown), unknown[:5],
            )
        tasks = [t for t in tasks if t in resume_set]
        if not tasks:
            raise ValueError("--resume-only with no eligible tasks in --task-set")

    # --- Refuse-on-prior-state gate (mode A) ---
    # Any task that is NOT listed in --resume-tasks but already has prior state
    # in its task_out_dir is ambiguous: did the user mean to resume it, or to
    # overwrite it? Refuse instead of silently doing either.
    overlap = resume_set & force_fresh_set
    if overlap:
        raise ValueError(
            f"--resume-tasks and --force-fresh overlap on: {sorted(overlap)}"
        )
    ambiguous: List[str] = []
    for tn in tasks:
        if tn in resume_set or tn in force_fresh_set:
            continue
        if _has_prior_state(out_dir / tn):
            ambiguous.append(tn)
    if ambiguous:
        sample = ambiguous[:5]
        raise ValueError(
            f"{len(ambiguous)} task(s) already have prior state under "
            f"{out_dir} but were not listed in --resume-tasks or --force-fresh "
            f"(examples: {sample}). Re-run with --resume-tasks <names> to "
            f"continue them, or --force-fresh <names> to discard prior state "
            f"and start over."
        )

    # --- Apply --force-fresh archival before any registration / docker run ---
    for tn in force_fresh_set:
        if tn not in tasks:
            logger.warning("--force-fresh task %s not in --task-set; ignored", tn)
            continue
        _archive_prior_state_for_force_fresh(out_dir / tn, tn)

    if resume_set:
        logger.info(
            "Resume requested for %d task(s); resume_only=%s",
            len(resume_set), resume_only,
        )
    if force_fresh_set:
        logger.info(
            "Force-fresh requested for %d task(s): %s",
            len(force_fresh_set), sorted(force_fresh_set)[:5],
        )

    logger.info(
        "Configuration: agent=%s, model=%s, mode=%s, timeout=%ds, "
        "setup_timeout=%ds, max_workers=%d, tasks=%d, eval_port=%d, "
        "skip_build=%s, gpu_devices=%s, external_eval=%s",
        agent_name, model, mode, timeout, setup_timeout, max_workers, len(tasks),
        eval_port, skip_build, gpu_devices_str or "none", use_external_eval,
    )

    # --- Start / connect Evaluation Service ---
    tracker = ScoreTracker()
    server = None
    # Track tasks rejected at register time (incomplete metadata / bad sota) so
    # we can skip running the agent for them and still report them in summary.
    pre_reject: Dict[str, Dict[str, Any]] = {}

    if use_external_eval:
        # External mode: register tasks with the correct eval service
        for task_name in tasks:
            task_path = data_dir / task_name
            if not task_path.exists():
                logger.warning("Task data directory not found: %s", task_path)
                continue
            port = task_port_map.get(task_name, default_eval_port)
            task_out_dir = out_dir / task_name
            task_out_dir.mkdir(parents=True, exist_ok=True)
            need_force = task_name in force_fresh_set
            status, payload = _register_task_with_service(
                port, task_name, str(task_path), timeout,
                out_dir=str(task_out_dir.resolve()),
                batch_name=out_dir.name,
                force=need_force,
            )
            if status == "ok":
                logger.info(
                    "[%s] Registered with eval service on port %d%s",
                    task_name, port, " (force=True)" if need_force else "",
                )
                # Also register locally for timer tracking
                tracker.register_task(
                    task_name, task_path, timeout=timeout, out_dir=task_out_dir,
                    force=need_force,
                )
            elif status == "incomplete_metadata":
                issues = (payload or {}).get("issues", [])
                logger.error(
                    "[%s] Skipped: metadata incomplete on eval service port %d (%d issues)",
                    task_name, port, len(issues),
                )
                pre_reject[task_name] = {
                    "task_name": task_name,
                    "status": "incomplete_metadata",
                    "duration": 0,
                    "metadata_issues": issues,
                }
            else:
                logger.error("[%s] Failed to register with eval service on port %d", task_name, port)
                pre_reject[task_name] = {
                    "task_name": task_name,
                    "status": "register_failed",
                    "duration": 0,
                }
    else:
        # Internal mode: start eval service in this process
        for task_name in tasks:
            task_path = data_dir / task_name
            if task_path.exists():
                task_out_dir = out_dir / task_name
                task_out_dir.mkdir(parents=True, exist_ok=True)
                tbl, issues = tracker.register_task(
                    task_name, task_path, timeout=timeout, out_dir=task_out_dir,
                    force=task_name in force_fresh_set,
                )
                for msg in issues:
                    logger.warning("[%s] METADATA: %s", task_name, msg)
                if not tbl:
                    logger.error("[%s] Skipped: metadata incomplete", task_name)
                    pre_reject[task_name] = {
                        "task_name": task_name,
                        "status": "incomplete_metadata",
                        "duration": 0,
                        "metadata_issues": issues,
                    }
            else:
                logger.warning("Task data directory not found: %s", task_path)
        server, _server_thread = start_server_background(eval_host, eval_port, tracker)
        logger.info("Evaluation Service started at http://%s:%d", eval_host, eval_port)

    # --- Helper to resolve per-task eval URL ---
    def _get_eval_url(task_name: str) -> str:
        port = task_port_map.get(task_name, default_eval_port)
        return f"http://host.docker.internal:{port}"

    # --- Run tasks ---
    total_start = time.time()
    results: List[Dict[str, Any]] = []
    results_lock = threading.Lock()
    summary_path = out_dir / "run_summary.json"

    def _enrich_result(r: Dict[str, Any]) -> None:
        """Enrich a single result with scores from eval service."""
        if use_external_eval:
            tn = r["task_name"]
            port = task_port_map.get(tn, default_eval_port)
            ext = _fetch_score_from_service(port, tn, batch_name=out_dir.name)
            if ext.get("best_attempt") is not None:
                r["best_attempt"] = ext["best_attempt"]
            if ext.get("best_aggregate_improvement") is not None:
                r["best_aggregate_improvement"] = ext["best_aggregate_improvement"]
            if ext.get("best_per_instance_improvement"):
                r["best_per_instance_improvement"] = ext["best_per_instance_improvement"]
            if ext.get("best_raw_scores"):
                r["best_raw_scores"] = ext["best_raw_scores"]
            if ext.get("total_attempts"):
                r["total_attempts"] = ext["total_attempts"]

    def _flush_summary() -> None:
        """Write current results to run_summary.json (caller must hold results_lock)."""
        total_duration = time.time() - total_start
        summary = _build_summary(list(results), tracker, total_duration)
        tmp_path = summary_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_path.replace(summary_path)

    def _record_result(r: Dict[str, Any]) -> None:
        """Enrich, append, and flush a completed task result."""
        _enrich_result(r)
        with results_lock:
            results.append(r)
            _flush_summary()

    def _get_score_str(task_name: str) -> str:
        """Get score string (best_aggregate_improvement) for a task."""
        score_info = tracker.get_task(task_name)
        if score_info and score_info.best_aggregate_improvement is not None:
            return f"{score_info.best_aggregate_improvement:+.4f}"
        if use_external_eval:
            port = task_port_map.get(task_name, default_eval_port)
            ext = _fetch_score_from_service(port, task_name, batch_name=out_dir.name)
            if ext.get("best_aggregate_improvement") is not None:
                return f"{ext['best_aggregate_improvement']:+.4f}"
        return "N/A"

    try:
        # Record pre-rejected tasks (metadata incomplete, register failed) first.
        for task_name, r in pre_reject.items():
            _record_result(r)
        runnable_tasks = [t for t in tasks if t not in pre_reject]

        # Helper: decide if a runnable task should be launched as a resume.
        def _decide_resume(task_name: str) -> bool:
            if task_name not in resume_set:
                return False
            ok, reason = _resume_eligible(out_dir / task_name, agent_name)

            if not ok:
                raise RuntimeError(
                    f"[{task_name}] resume requested but not eligible: {reason}"
                )
            return True

        if max_workers == 1:
            for task_name in tqdm(runnable_tasks, desc="Solving tasks"):
                eval_url = _get_eval_url(task_name)
                is_resume = _decide_resume(task_name)
                r = _run_single_task(
                    task_name, data_dir, out_dir,
                    agent_name, model, mode,
                    eval_url, timeout, gpu_allocator,
                    tracker=tracker,
                    skip_build=skip_build,
                    base_image=base_image,
                    dockerfile_name=dockerfile_name,
                    is_resume=is_resume,
                    setup_timeout=setup_timeout,
                    codex_auth_dir=codex_auth_dir,
                    codex_use_api_key=codex_use_api_key,
                    proxy_mode=proxy_mode,
                    proxy_container=proxy_container,
                    proxy_network=proxy_network,
                    proxy_bundle=proxy_bundle,
                    proxy_http_port=proxy_http_port,
                    proxy_socks_port=proxy_socks_port,
                )
                _record_result(r)
                score_str = _get_score_str(task_name)
                logger.info(
                    "[%s] Done: status=%s, duration=%.1fs, best_aggregate_improvement=%s%s",
                    task_name, r["status"], r["duration"], score_str,
                    " [resume]" if is_resume else "",
                )
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(
                        _run_single_task,
                        task_name, data_dir, out_dir,
                        agent_name, model, mode,
                        _get_eval_url(task_name), timeout, gpu_allocator,
                        tracker,
                        skip_build,
                        base_image,
                        dockerfile_name,
                        is_resume=_decide_resume(task_name),
                        setup_timeout=setup_timeout,
                        codex_auth_dir=codex_auth_dir,
                        codex_use_api_key=codex_use_api_key,
                        proxy_mode=proxy_mode,
                        proxy_container=proxy_container,
                        proxy_network=proxy_network,
                        proxy_bundle=proxy_bundle,
                        proxy_http_port=proxy_http_port,
                        proxy_socks_port=proxy_socks_port,
                    ): task_name
                    for task_name in runnable_tasks
                }

                pbar = tqdm(total=len(futures), desc="Solving tasks")
                for future in as_completed(futures):
                    pbar.update(1)
                    task_name = futures[future]
                    try:
                        r = future.result()
                    except Exception as exc:
                        logger.error("[%s] Unexpected error: %s", task_name, exc)
                        r = {
                            "task_name": task_name,
                            "status": "error",
                            "message": str(exc),
                            "duration": 0,
                        }
                    score_str = _get_score_str(task_name)
                    pbar.write(
                        f"[{task_name}] status={r['status']}, "
                        f"duration={r['duration']:.1f}s, best_aggregate_improvement={score_str}"
                    )
                    _record_result(r)
                pbar.close()

    finally:
        if server is not None:
            logger.info("Shutting down Evaluation Service...")
            server.shutdown()
        # Best-effort cross-process GPU pool cleanup. In-memory pool is GC'd.
        if gpu_allocator is not None and hasattr(gpu_allocator, "release_all"):
            try:
                gpu_allocator.release_all()
            except Exception as e:
                logger.warning("GPU allocator release_all failed: %s", e)

    # --- Drain pending /evaluate calls and re-enrich results from eval service ---
    # /evaluate is synchronous on the service side, so a curl POST blocks until
    # the evaluator finishes. Each task's in-flight evaluation is already drained
    # per-task by _wait_eval_drain (it polls /time_remaining until is_paused
    # flips False before /pause_timer), so by the time we get here every task's
    # evaluator has finished and its score is recorded server-side.
    # This short sleep is only a small buffer to cover the narrow race where the
    # last task's container exits before the eval service registers its final
    # /evaluate as in-flight; we then re-fetch each task's score.
    if use_external_eval:
        _DRAIN_WAIT_SECONDS = 10  # short buffer; per-task _wait_eval_drain already drained each task
        logger.info(
            "Waiting %ds for eval_service to drain pending evaluators "
            "before re-enriching scores...", _DRAIN_WAIT_SECONDS,
        )
        time.sleep(_DRAIN_WAIT_SECONDS)
        for r in results:
            try:
                _enrich_result(r)
            except Exception as e:
                logger.warning(
                    "[%s] re-enrich after drain failed: %s",
                    r.get("task_name", "?"), e,
                )

    # --- Post-hoc LLM judge (scientific validity check) ---
    if not skip_judge:
        try:
            from judge import run_judges, apply_verdicts_to_results
            judge_targets: List[Tuple[str, Path]] = []
            for r in results:
                tn = r.get("task_name")
                if tn is None:
                    continue
                if r.get("best_aggregate_improvement") is None:
                    continue  # no submission to review
                judge_targets.append((tn, out_dir / tn))
            if judge_targets:
                logger.info("Running post-hoc judge on %d task(s)...", len(judge_targets))
                verdicts = run_judges(
                    judge_targets,
                    agent_name=agent_name,
                    max_workers=min(4, len(judge_targets)),
                    data_dir=data_dir,
                )
                apply_verdicts_to_results(results, verdicts)
        except Exception as e:
            logger.exception("Judge stage failed: %s", e)

    # --- Final flush (ensure all results are written) ---
    with results_lock:
        _flush_summary()

    # Print final report
    total_duration = time.time() - total_start
    scored = [r for r in results if r.get("best_aggregate_improvement") is not None]
    valid_scored = [r for r in scored if r.get("effective_improvement") is not None]
    print(f"\n{'='*60}")
    print(f"Solve complete. Results saved to {summary_path}")
    print(f"Total tasks: {len(results)}, Scored: {len(scored)}, Valid-scored: {len(valid_scored)}")
    print(f"Total duration: {total_duration:.1f}s")
    if scored:
        print(f"\nbest_aggregate_improvement (vs SOTA, +/-):")
        for r in scored:
            judge = r.get("judge")
            if judge is None:
                tag = ""
            elif judge.get("is_valid") is True:
                tag = " [valid]"
            elif judge.get("is_valid") is False:
                tag = " [INVALID — discarded]"
            else:
                tag = " [judge error]"
            print(f"  {r['task_name']}: {r['best_aggregate_improvement']:+.4f} "
                  f"({r.get('total_attempts', 0)} attempts){tag}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
