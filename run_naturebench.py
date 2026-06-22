#!/usr/bin/env python3
"""One-command launcher for NatureBench.

The public dataset is expected to contain fully packaged tasks under
``tasks/<case_id>/``. This wrapper handles dataset download, optional eval
service startup, GPU scheduling flags, resume/fresh-run controls, and then
delegates execution to ``solve.py``.
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config_loader import load_yaml_config, merge_args_with_config


DEFAULT_DATASET_ID = "FrontisAI/NatureBench"


def _run(cmd: list[str], *, cwd: Path, dry_run: bool = False) -> None:
    rendered = " ".join(shlex.quote(x) for x in cmd)
    print("+ " + rendered, flush=True)
    if not dry_run:
        subprocess.run(cmd, cwd=str(cwd), check=True)


def _read_task_file(path: Path) -> list[str]:
    tasks: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            tasks.append(line)
    return tasks


def _download_dataset(
    dataset_id: str,
    data_dir: Path,
    revision: str | None,
    task_ids: list[str],
    dry_run: bool,
) -> None:
    allow_patterns = ["README.md", "LICENSE", "manifest.jsonl"]
    allow_patterns.extend(f"tasks/{task_id}/**" for task_id in task_ids)

    if dry_run:
        print(f"[dry-run] would download {len(task_ids)} task(s) from {dataset_id} to {data_dir}")
        return
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise SystemExit(
            "huggingface_hub is required for dataset download. "
            "Create and activate the release environment with: "
            "conda env create -f conda_env.yml && conda activate cnsbench"
        ) from exc

    snapshot_download(
        repo_id=dataset_id,
        repo_type="dataset",
        revision=revision,
        local_dir=str(data_dir),
        local_dir_use_symlinks=False,
        allow_patterns=allow_patterns,
    )


def _resolve_tasks_dir(dataset_root: Path) -> Path:
    tasks_dir = dataset_root / "tasks"
    return tasks_dir if tasks_dir.is_dir() else dataset_root


def _slug(text: str) -> str:
    keep = []
    for ch in text:
        keep.append(ch if ch.isalnum() or ch in ("-", "_", ".") else "_")
    return "".join(keep).strip("_") or "run"


def _append_option(cmd: list[str], flag: str, value: object | None) -> None:
    if value is not None and value != "":
        cmd.extend([flag, str(value)])


def _append_list(cmd: list[str], flag: str, values: list[str]) -> None:
    if values:
        cmd.append(flag)
        cmd.extend(values)


def _explicit_arg_keys(argv: list[str]) -> set[str]:
    keys: set[str] = set()
    for token in argv:
        if token == "--":
            break
        if not token.startswith("--") or token == "--":
            continue
        name = token[2:].split("=", 1)[0]
        if name:
            keys.add(name.replace("-", "_"))
    return keys


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Download NatureBench data if needed and launch solve.py.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        default=None,
        help=(
            "YAML config. If omitted, ./config.yaml is used when it exists. "
            "Values are read from the 'run' section; CLI args override."
        ),
    )

    data = parser.add_argument_group("data")
    data.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    data.add_argument(
        "--dataset-revision",
        default=None,
        help="Dataset branch, tag, or commit. Default None uses the HF default branch.",
    )
    data.add_argument("--data-dir", default="./data/naturebench_data")
    data.add_argument("--skip-download", action="store_true")
    data.add_argument(
        "--download-only",
        action="store_true",
        help="Only download selected tasks; --agent and --model are not required.",
    )

    run = parser.add_argument_group("run selection")
    run.add_argument(
        "--tasks",
        default="all",
        help=(
            "Task selection. Use one of all/cpu/gpu_high/gpu_low, or pass a "
            "custom task-set file path. The wrapper converts this to solve.py "
            "--task-set internally."
        ),
    )
    run.add_argument("--batch-name", default=None, help="Used to derive --out-dir when --out-dir is omitted.")
    run.add_argument("--out-dir", default=None)
    run.add_argument("--dry-run", action="store_true", help="Print commands without running them.")

    agent = parser.add_argument_group("agent")
    agent.add_argument(
        "--agent",
        choices=["claude", "codex", "gemini"],
        default=None,
        help="Agent harness. Required unless --download-only is used.",
    )
    agent.add_argument(
        "--model",
        default=None,
        help="Model name passed to the agent CLI. Required unless --download-only is used.",
    )
    agent.add_argument("--mode", default="base", choices=["base", "reproduce"])
    agent.add_argument("--timeout", type=int, default=14400)
    agent.add_argument("--setup-timeout", type=int, default=1800)
    agent.add_argument("--max-workers", type=int, default=1)

    docker = parser.add_argument_group("docker and task setup")
    docker.add_argument("--skip-build", dest="skip_build", action="store_true", default=True)
    docker.add_argument("--build-task-images", dest="skip_build", action="store_false")
    docker.add_argument("--base-image", default="naturebench-base:v3")
    docker.add_argument("--dockerfile-name", default="Dockerfile.v3")
    docker.add_argument("--ensure-base-image", action="store_true")

    eval_group = parser.add_argument_group("evaluation service")
    eval_group.add_argument("--eval-port", type=int, default=None)
    eval_group.add_argument("--eval-env-mapping", default=None)
    eval_group.add_argument("--start-eval-services", action="store_true")
    eval_group.add_argument("--eval-log-dir", default=None)
    eval_group.add_argument("--skip-judge", action="store_true")

    gpu = parser.add_argument_group("gpu scheduling")
    gpu.add_argument("--gpu-devices", default=None, help="Comma-separated GPU ids, e.g. 0,1,2,3.")
    gpu.add_argument("--gpu-pool-file", default=None)
    gpu.add_argument("--gpu-skip-busy-mb", type=int, default=None)
    gpu.add_argument("--gpu-skip-busy-util", type=int, default=None)
    gpu.add_argument("--shared-gpu-task-file", default=None)
    gpu.add_argument("--shared-gpu-device", type=int, default=None)
    gpu.add_argument("--shared-gpu-slots", type=int, default=None)
    gpu.add_argument("--shared-gpu-pool-file", default=None)

    resume = parser.add_argument_group("resume and rerun")
    resume.add_argument("--resume-tasks", nargs="*", default=[])
    resume.add_argument("--resume-task-file", default=None)
    resume.add_argument("--resume-only", action="store_true")
    resume.add_argument("--force-fresh", nargs="*", default=[])
    resume.add_argument("--force-fresh-task-file", default=None)

    proxy = parser.add_argument_group("network proxy")
    proxy.add_argument("--proxy-mode", choices=["host", "sidecar", "embedded", "none"], default=None)
    proxy.add_argument("--proxy-bundle", default=None)
    proxy.add_argument("--proxy-container", default=None)
    proxy.add_argument("--proxy-network", default=None)
    proxy.add_argument("--proxy-http-port", type=int, default=None)
    proxy.add_argument("--proxy-socks-port", type=int, default=None)

    codex = parser.add_argument_group("codex")
    codex.add_argument("--codex-auth-dir", default=None)
    codex.add_argument("--codex-auth-mode", choices=["api-key", "device-auth"], default=None)

    parser.add_argument(
        "solve_args",
        nargs=argparse.REMAINDER,
        help="Extra arguments passed through to solve.py after '--'.",
    )
    args = parser.parse_args()
    explicit_keys = _explicit_arg_keys(sys.argv[1:])

    config_path: Path | None = None
    if args.config:
        config_path = Path(args.config).expanduser().resolve()
    else:
        default_config = root / "config.yaml"
        if default_config.exists():
            config_path = default_config
    if config_path is not None:
        config_data = load_yaml_config(str(config_path))
        args = merge_args_with_config(
            parser,
            args,
            config_data,
            section="run",
            explicit_keys=explicit_keys,
        )

    if args.tasks in {"all", "cpu", "gpu_high", "gpu_low"}:
        task_set = root / "task-set" / f"{args.tasks}.txt"
        task_line_for_name = args.tasks
    else:
        task_set = Path(args.tasks).expanduser().resolve()
        task_line_for_name = Path(args.tasks).stem
    if not task_set.is_file():
        raise SystemExit(f"Task-set file not found: {task_set}")
    selected_tasks = _read_task_file(task_set)

    data_root = Path(args.data_dir).expanduser().resolve()
    if not args.skip_download:
        _download_dataset(args.dataset_id, data_root, args.dataset_revision, selected_tasks, args.dry_run)
    tasks_dir = _resolve_tasks_dir(data_root)
    if args.download_only:
        print(f"Dataset root: {data_root}")
        print(f"Task packages: {tasks_dir}")
        print(f"Selected tasks: {len(selected_tasks)}")
        return

    if not args.agent:
        raise SystemExit("Agent is required unless --download-only is used. Pass --agent.")
    if not args.model:
        raise SystemExit("Model name is required unless --download-only is used. Pass --model.")

    if args.out_dir:
        out_dir = Path(args.out_dir).expanduser().resolve()
    else:
        batch_name = args.batch_name
        if not batch_name:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_name = f"{args.agent}_{_slug(args.model)}_{_slug(task_line_for_name)}_{stamp}"
        out_dir = (root / "results" / batch_name).resolve()

    if args.force_fresh_task_file:
        args.force_fresh.extend(_read_task_file(Path(args.force_fresh_task_file).expanduser()))

    if args.ensure_base_image:
        _run(["bash", str(root / "scripts" / "ensure_naturebench_base.sh")], cwd=root, dry_run=args.dry_run)

    mapping_path = Path(args.eval_env_mapping).expanduser().resolve() if args.eval_env_mapping else None
    if args.start_eval_services:
        if mapping_path is None:
            raise SystemExit("--start-eval-services requires --eval-env-mapping.")
        cmd = ["bash", str(root / "scripts" / "start_eval_services.sh"), str(mapping_path)]
        if args.eval_log_dir:
            cmd.extend(["--log-dir", str(Path(args.eval_log_dir).expanduser().resolve())])
        _run(cmd, cwd=root, dry_run=args.dry_run)

    solve_cmd = [
        sys.executable,
        str(root / "solve.py"),
        "--task-set",
        str(task_set),
        "--data-dir",
        str(tasks_dir),
        "--out-dir",
        str(out_dir),
        "--agent",
        args.agent,
        "--model",
        args.model,
        "--mode",
        args.mode,
        "--timeout",
        str(args.timeout),
        "--setup-timeout",
        str(args.setup_timeout),
        "--max-workers",
        str(args.max_workers),
        "--base-image",
        args.base_image,
        "--dockerfile-name",
        args.dockerfile_name,
    ]
    if args.skip_build:
        solve_cmd.append("--skip-build")
    if args.skip_judge:
        solve_cmd.append("--skip-judge")

    _append_option(solve_cmd, "--eval-port", args.eval_port)
    if mapping_path is not None:
        solve_cmd.extend(["--eval-env-mapping", str(mapping_path)])

    _append_option(solve_cmd, "--gpu-devices", args.gpu_devices)
    _append_option(solve_cmd, "--gpu-pool-file", args.gpu_pool_file)
    _append_option(solve_cmd, "--gpu-skip-busy-mb", args.gpu_skip_busy_mb)
    _append_option(solve_cmd, "--gpu-skip-busy-util", args.gpu_skip_busy_util)
    _append_option(solve_cmd, "--shared-gpu-task-file", args.shared_gpu_task_file)
    _append_option(solve_cmd, "--shared-gpu-device", args.shared_gpu_device)
    _append_option(solve_cmd, "--shared-gpu-slots", args.shared_gpu_slots)
    _append_option(solve_cmd, "--shared-gpu-pool-file", args.shared_gpu_pool_file)

    _append_list(solve_cmd, "--resume-tasks", args.resume_tasks)
    _append_option(solve_cmd, "--resume-task-file", args.resume_task_file)
    if args.resume_only:
        solve_cmd.append("--resume-only")
    _append_list(solve_cmd, "--force-fresh", args.force_fresh)

    _append_option(solve_cmd, "--proxy-mode", args.proxy_mode)
    _append_option(solve_cmd, "--proxy-bundle", args.proxy_bundle)
    _append_option(solve_cmd, "--proxy-container", args.proxy_container)
    _append_option(solve_cmd, "--proxy-network", args.proxy_network)
    _append_option(solve_cmd, "--proxy-http-port", args.proxy_http_port)
    _append_option(solve_cmd, "--proxy-socks-port", args.proxy_socks_port)

    _append_option(solve_cmd, "--codex-auth-dir", args.codex_auth_dir)
    _append_option(solve_cmd, "--codex-auth-mode", args.codex_auth_mode)

    if args.solve_args:
        extra = args.solve_args
        if extra and extra[0] == "--":
            extra = extra[1:]
        solve_cmd.extend(extra)

    print(f"Task packages: {tasks_dir}")
    print(f"Task-set: {task_set}")
    print(f"Output dir: {out_dir}")
    _run(solve_cmd, cwd=root, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
