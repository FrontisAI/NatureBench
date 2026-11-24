#!/usr/bin/env python3
"""Download and materialize the compressed NatureBench Harbor task dataset."""

from __future__ import annotations

import argparse
import re
import shutil
import tarfile
from pathlib import Path
from typing import Iterable


DEFAULT_REPO_ID = "FrontisAI/NatureBench-Harbor"
TASK_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
COMPUTE_GROUPS = ("cpu", "gpu_low", "gpu_high")
DEFAULT_TASK_SET_DIR = (
    Path(__file__).resolve().parents[1]
    / "adapter"
    / "src"
    / "naturebench_adapter"
    / "source_data"
    / "task_set"
)


class ReleaseError(RuntimeError):
    """Raised when a downloaded Harbor release is incomplete or unsafe."""


def task_ids_for_compute_groups(
    compute_groups: Iterable[str],
    task_set_dir: Path = DEFAULT_TASK_SET_DIR,
) -> list[str]:
    """Return the task IDs assigned to the requested compute groups."""

    selected: set[str] = set()
    for compute_group in dict.fromkeys(compute_groups):
        if compute_group not in COMPUTE_GROUPS:
            raise ReleaseError(f"unknown compute group: {compute_group}")
        task_set = task_set_dir / f"{compute_group}.txt"
        if not task_set.is_file():
            raise ReleaseError(f"missing compute-group task set: {task_set}")
        task_ids = [
            line.strip()
            for line in task_set.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        invalid = sorted(
            task_id for task_id in task_ids if not TASK_ID_PATTERN.fullmatch(task_id)
        )
        if invalid:
            raise ReleaseError(
                f"invalid task IDs in compute group {compute_group}: "
                + ", ".join(invalid)
            )
        if len(task_ids) != len(set(task_ids)):
            raise ReleaseError(f"duplicate task IDs in compute group: {compute_group}")
        overlap = selected.intersection(task_ids)
        if overlap:
            raise ReleaseError(
                "task IDs assigned to multiple selected compute groups: "
                + ", ".join(sorted(overlap))
            )
        selected.update(task_ids)
    if not selected:
        raise ReleaseError("no compute groups selected")
    return sorted(selected)


def extract_task_archives(
    archives: Iterable[Path], output_dir: Path, task_id: str
) -> None:
    """Remove any existing task directory and extract the selected archives."""

    if not TASK_ID_PATTERN.fullmatch(task_id):
        raise ReleaseError(f"invalid task ID: {task_id}")
    archives = list(archives)
    if not archives:
        raise ReleaseError(f"no archives provided for task: {task_id}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    target_task = output_dir / task_id
    if target_task.is_symlink() or (target_task.exists() and not target_task.is_dir()):
        raise ReleaseError(f"expected a regular task directory: {target_task}")
    if any(path.resolve().is_relative_to(target_task) for path in archives):
        raise ReleaseError(f"source archive is inside the task directory: {target_task}")
    if target_task.is_dir():
        shutil.rmtree(target_task)

    def task_filter(member: tarfile.TarInfo, destination: str) -> tarfile.TarInfo | None:
        member = tarfile.data_filter(member, destination)
        if member is None:
            return None
        path = output_dir / member.name
        resolved = path.resolve()
        if not resolved.is_relative_to(target_task):
            raise tarfile.FilterError(f"archive member outside {task_id}/: {member.name}")
        if resolved == target_task and not member.isdir():
            raise tarfile.FilterError(f"expected a task directory: {member.name}")
        if member.issym() or member.islnk():
            link_root = path.parent if member.issym() else output_dir
            if not (link_root / member.linkname).resolve().is_relative_to(target_task):
                raise tarfile.FilterError(f"archive link outside {task_id}/: {member.name}")
        return member

    for archive in archives:
        try:
            with tarfile.open(archive, "r:gz") as handle:
                handle.extractall(output_dir, filter=task_filter)
        except (OSError, EOFError, tarfile.TarError) as error:
            raise ReleaseError(f"failed to extract {archive}: {error}") from error
    if not (target_task / "task.toml").is_file():
        raise ReleaseError(f"archives for {task_id} do not contain {task_id}/task.toml")


def _selected_archives(
    release_dir: Path,
    task_ids: Iterable[str] | None,
) -> list[tuple[str, list[Path]]]:
    requested = set(task_ids or ())
    invalid = sorted(
        task_id for task_id in requested if not TASK_ID_PATTERN.fullmatch(task_id)
    )
    if invalid:
        raise ReleaseError("invalid task IDs: " + ", ".join(invalid))
    archive_root = release_dir / "task_archives"
    if not archive_root.is_dir():
        raise ReleaseError(f"missing task archive directory: {archive_root}")

    available: dict[str, list[Path]] = {}
    for archive in sorted(archive_root.glob("*.tar.gz")):
        task_id = archive.name[: -len(".tar.gz")]
        if TASK_ID_PATTERN.fullmatch(task_id):
            available[task_id] = [archive]

    for part_dir in sorted(archive_root.iterdir()):
        if not part_dir.is_dir() or not TASK_ID_PATTERN.fullmatch(part_dir.name):
            continue
        archives = sorted(part_dir.glob("*.tar.gz"))
        if not archives:
            continue
        task_id = part_dir.name
        if task_id in available:
            raise ReleaseError(
                f"task has both a single archive and archive parts: {task_id}"
            )
        available[task_id] = archives

    missing = sorted(requested - available.keys())
    if missing:
        raise ReleaseError("unknown task IDs: " + ", ".join(missing))
    selected = {
        task_id: archives
        for task_id, archives in available.items()
        if not requested or task_id in requested
    }
    if not selected:
        raise ReleaseError("no task archives selected")
    return sorted(selected.items())


def materialize_release(
    release_dir: Path,
    output_dir: Path,
    *,
    task_ids: Iterable[str] | None,
) -> None:
    release_dir = release_dir.resolve()
    output_dir = output_dir.resolve()
    dataset_toml = release_dir / "dataset.toml"
    if not dataset_toml.is_file():
        raise ReleaseError(f"missing dataset.toml: {dataset_toml}")
    selected = _selected_archives(release_dir, task_ids)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "dataset.toml").write_bytes(dataset_toml.read_bytes())

    for index, (task_id, archive_parts) in enumerate(selected, 1):
        extract_task_archives(archive_parts, output_dir, task_id)
        print(f"[{index}/{len(selected)}] installed {task_id}", flush=True)


def download_snapshot(
    repo_id: str,
    revision: str | None,
    cache_dir: Path | None,
    task_ids: Iterable[str] | None,
) -> Path:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as error:
        raise ReleaseError(
            "huggingface_hub is required for download; install it with "
            "`python -m pip install huggingface_hub`"
        ) from error
    requested = list(task_ids or ())
    invalid = sorted(
        task_id for task_id in requested if not TASK_ID_PATTERN.fullmatch(task_id)
    )
    if invalid:
        raise ReleaseError("invalid task IDs: " + ", ".join(invalid))
    archive_patterns = (
        [
            pattern
            for task_id in requested
            for pattern in (
                f"task_archives/{task_id}.tar.gz",
                f"task_archives/{task_id}/*.tar.gz",
            )
        ]
        if requested
        else ["task_archives/*.tar.gz", "task_archives/*/*.tar.gz"]
    )
    snapshot = snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
        cache_dir=str(cache_dir) if cache_dir else None,
        allow_patterns=["dataset.toml", *archive_patterns],
    )
    return Path(snapshot)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--release-dir", type=Path, help="Use an existing HF snapshot")
    source.add_argument("--repo-id", default=DEFAULT_REPO_ID, help="HF dataset repository")
    parser.add_argument("--revision", help="HF branch, tag, or commit")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--task-ids", nargs="*")
    selection.add_argument(
        "--compute",
        nargs="+",
        choices=COMPUTE_GROUPS,
        help="Download one or more NatureBench compute groups",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        task_ids = (
            task_ids_for_compute_groups(args.compute)
            if args.compute
            else args.task_ids
        )
        release_dir = args.release_dir or download_snapshot(
            args.repo_id, args.revision, args.cache_dir, task_ids
        )
        materialize_release(release_dir, args.output_dir, task_ids=task_ids)
    except (ReleaseError, OSError) as error:
        print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
