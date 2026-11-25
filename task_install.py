"""Install validated NatureBench task packages on the destination filesystem."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def list_dataset_files(repo_id: str, revision: str | None) -> tuple[str, list[str]]:
    """Resolve a dataset revision once and list files at the resolved commit."""
    from huggingface_hub import HfApi

    api = HfApi()
    commit = api.repo_info(repo_id, repo_type="dataset", revision=revision).sha
    if not commit:
        raise RuntimeError(f"Could not resolve a commit for dataset {repo_id}")
    return commit, api.list_repo_files(repo_id, repo_type="dataset", revision=commit)


def publish_replacement(source: Path, target: Path) -> None:
    """Replace one installed task and restore its previous directory on failure."""
    if not target.exists() and not target.is_symlink():
        os.replace(source, target)
        return

    backup = Path(tempfile.mkdtemp(prefix=".naturebench-backup-", dir=target.parent))
    previous = backup / target.name
    cleanup_backup = True
    try:
        os.replace(target, previous)
        os.replace(source, target)
    except BaseException as install_error:
        if previous.exists() or previous.is_symlink():
            try:
                os.replace(previous, target)
            except OSError as rollback_error:
                cleanup_backup = False
                raise OSError(
                    f"Install failed ({install_error}). Could not restore {target}. "
                    f"Previous files are in {backup}: {rollback_error}"
                ) from install_error
        raise
    finally:
        if cleanup_backup:
            shutil.rmtree(backup)
