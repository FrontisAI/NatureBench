#!/usr/bin/env python3
"""Download and materialize the compressed NatureBench Harbor task dataset."""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
import tempfile
from functools import partial
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable

# The documented CLI runs this file directly from the harbor/ subdirectory.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from task_install import list_dataset_files, publish_replacement


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
    """Install one task, retaining the old copy until extraction succeeds."""
    output_dir = output_dir.resolve()
    archives = _validate_task_destination(archives, output_dir, task_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".naturebench-stage-", dir=output_dir) as stage:
        staged = _extract_task_archives(archives, Path(stage), task_id)
        publish_replacement(staged, output_dir / task_id)


def _validate_task_destination(
    archives: Iterable[Path], output_dir: Path, task_id: str
) -> list[Path]:
    if not TASK_ID_PATTERN.fullmatch(task_id):
        raise ReleaseError(f"invalid task ID: {task_id}")
    archives = list(archives)
    if not archives:
        raise ReleaseError(f"no archives provided for task: {task_id}")
    target_task = output_dir / task_id
    if target_task.is_symlink() or (target_task.exists() and not target_task.is_dir()):
        raise ReleaseError(f"expected a regular task directory: {target_task}")
    if any(path.resolve().is_relative_to(target_task) for path in archives):
        raise ReleaseError(f"source archive is inside the task directory: {target_task}")
    return archives


def _extract_task_archives(archives: list[Path], output_dir: Path, task_id: str) -> Path:
    target_task = output_dir / task_id

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
    return target_task


def _selected_archives(
    filenames: Iterable[str],
    task_ids: Iterable[str] | None,
) -> list[tuple[str, list[str]]]:
    requested = set(task_ids or ())
    invalid = sorted(task_id for task_id in requested if not TASK_ID_PATTERN.fullmatch(task_id))
    if invalid:
        raise ReleaseError("invalid task IDs: " + ", ".join(invalid))

    available: dict[str, list[str]] = {}
    for filename in filenames:
        path = PurePosixPath(filename)
        if len(path.parts) not in (2, 3) or path.parts[0] != "task_archives":
            continue
        if not path.name.endswith(".tar.gz"):
            continue
        task_id = path.name.removesuffix(".tar.gz") if len(path.parts) == 2 else path.parts[1]
        if TASK_ID_PATTERN.fullmatch(task_id):
            available.setdefault(task_id, []).append(filename)

    selected = requested or available.keys()
    if not selected:
        raise ReleaseError("no task archives selected")
    return [(task_id, sorted(available.get(task_id, []))) for task_id in sorted(selected)]


def _install_release_tasks(
    selected: list[tuple[str, list[str]]],
    fetch_archive: Callable[[str], Path],
    dataset_toml: bytes,
    output_dir: Path,
) -> None:
    output_dir = output_dir.resolve()
    target_manifest = output_dir / "dataset.toml"
    if target_manifest.is_symlink() or (target_manifest.exists() and not target_manifest.is_file()):
        raise ReleaseError(f"expected a regular manifest file: {target_manifest}")

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".naturebench-stage-", dir=output_dir) as stage:
        staged_manifest = Path(stage) / "dataset.toml"
        staged_manifest.write_bytes(dataset_toml)
        staged_manifest.replace(target_manifest)

    failed = []
    for index, (task_id, filenames) in enumerate(selected, 1):
        try:
            if not filenames:
                raise ReleaseError(f"no archives found for task {task_id}")
            if len(filenames) > 1 and f"task_archives/{task_id}.tar.gz" in filenames:
                raise ReleaseError(f"task has both a single archive and archive parts: {task_id}")
            extract_task_archives((fetch_archive(filename) for filename in filenames), output_dir, task_id)
        except Exception as error:
            failed.append(task_id)
            print(f"ERROR: {task_id}: {error}", flush=True)
        else:
            print(f"[{index}/{len(selected)}] installed {task_id}", flush=True)
    if failed:
        raise ReleaseError("failed to install tasks: " + ", ".join(failed))


def materialize_release(
    release_dir: Path,
    output_dir: Path,
    *,
    task_ids: Iterable[str] | None,
) -> None:
    release_dir = release_dir.resolve()
    dataset_toml = release_dir / "dataset.toml"
    if not dataset_toml.is_file():
        raise ReleaseError(f"missing dataset.toml: {dataset_toml}")
    if not (release_dir / "task_archives").is_dir():
        raise ReleaseError(f"missing task archive directory: {release_dir / 'task_archives'}")
    archives = (
        path.relative_to(release_dir).as_posix()
        for pattern in ("task_archives/*.tar.gz", "task_archives/*/*.tar.gz")
        for path in release_dir.glob(pattern)
    )
    selected = _selected_archives(archives, task_ids)
    _install_release_tasks(selected, release_dir.joinpath, dataset_toml.read_bytes(), output_dir)


def download_release(
    repo_id: str,
    revision: str | None,
    cache_dir: Path | None,
    output_dir: Path,
    task_ids: Iterable[str] | None,
) -> None:
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as error:
        raise ReleaseError(
            "huggingface_hub is required for download; install it with "
            "`python -m pip install huggingface_hub`"
        ) from error
    try:
        commit, filenames = list_dataset_files(repo_id, revision)
        fetch = partial(
            hf_hub_download, repo_id=repo_id, repo_type="dataset",
            revision=commit, cache_dir=cache_dir,
        )
        dataset_toml = Path(fetch(filename="dataset.toml")).read_bytes()
    except Exception as error:
        raise ReleaseError(f"failed to open dataset {repo_id}: {error}") from error
    selected = _selected_archives(filenames, task_ids)
    _install_release_tasks(
        selected, lambda filename: Path(fetch(filename=filename)), dataset_toml, output_dir
    )


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
        if args.release_dir:
            materialize_release(args.release_dir, args.output_dir, task_ids=task_ids)
        else:
            download_release(args.repo_id, args.revision, args.cache_dir, args.output_dir, task_ids)
    except (ReleaseError, OSError) as error:
        print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
