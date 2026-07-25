"""Collect source-like workspace evidence for validity judging."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set

from judge_core.policy import (
    MAX_BYTES_PER_SOURCE_FILE,
    MAX_SOURCE_FILES,
    MAX_SOURCE_TOTAL_BYTES,
)


def read_clip(path: Path, max_bytes: int) -> str:
    """Read a text file under a hard UTF-8 byte limit."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return f"[failed to read {path}: {error}]"
    return clip_text_bytes(text, max_bytes)


SOURCE_SUFFIXES: Set[str] = {
    ".py",
    ".sh",
    ".bash",
    ".r",
    ".jl",
    ".m",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".yaml",
    ".yml",
    ".toml",
    ".ipynb",
}
SOURCE_FILENAMES: Set[str] = {"Makefile"}
SOURCE_SKIP_DIRS: Set[str] = {
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "site-packages",
    "output",
    "outputs",
    "data",
    "checkpoints",
    ".cache",
    "cache",
}
SOURCE_ENTRY_NAMES: Set[str] = {
    "run.py",
    "solution.py",
    "main.py",
    "train.py",
    "Makefile",
}


def clip_text_bytes(text: str, max_bytes: int) -> str:
    """Clip UTF-8 text to a hard byte limit while preserving head and tail."""
    if max_bytes <= 0:
        return ""
    data = text.encode("utf-8")
    if len(data) <= max_bytes:
        return text
    marker = f"\n\n... [{len(data) - max_bytes} bytes elided] ...\n\n"
    marker_bytes = marker.encode("utf-8")
    if len(marker_bytes) >= max_bytes:
        return marker_bytes[:max_bytes].decode("utf-8", errors="ignore")
    content_budget = max_bytes - len(marker_bytes)
    head_n = content_budget // 2
    tail_n = content_budget - head_n
    head = data[:head_n].decode("utf-8", errors="ignore")
    tail = data[-tail_n:].decode("utf-8", errors="ignore")
    return head + marker + tail


def _read_source_file(path: Path) -> str:
    """Read a source-like file; notebooks contribute code cells only."""
    if path.suffix.lower() != ".ipynb":
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            return f"[failed to read {path}: {error}]"
        return clip_text_bytes(text, MAX_BYTES_PER_SOURCE_FILE)
    try:
        notebook = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError) as error:
        return clip_text_bytes(
            f"[failed to read {path}: {error}]",
            MAX_BYTES_PER_SOURCE_FILE,
        )
    if not isinstance(notebook, dict) or not isinstance(notebook.get("cells"), list):
        return clip_text_bytes(
            f"[invalid notebook schema: {path}]",
            MAX_BYTES_PER_SOURCE_FILE,
        )
    code_cells: List[str] = []
    for index, cell in enumerate(notebook.get("cells") or []):
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        source = cell.get("source") or ""
        if isinstance(source, list):
            source = "".join(str(part) for part in source)
        if isinstance(source, str) and source.strip():
            code_cells.append(f"# Notebook code cell {index}\n{source}")
    return clip_text_bytes(
        "\n\n".join(code_cells),
        MAX_BYTES_PER_SOURCE_FILE,
    )


def collect_source_files(workspace_dir: Path) -> Dict[str, str]:
    """Collect agent-authored source-like files under one shared budget.

    The final workspace is supplementary evidence, so all supported source
    types share the same file-count and total-byte limits. Python files rank
    first, shell files second, and other supported types third. Within each
    type group, shallower paths and entry points rank first.
    """
    files: Dict[str, str] = {}
    if not workspace_dir.exists():
        return files
    candidates = []
    for path in workspace_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            relpath = path.relative_to(workspace_dir)
        except ValueError:
            continue
        if any(part in SOURCE_SKIP_DIRS for part in relpath.parts[:-1]):
            continue
        if path.name not in SOURCE_FILENAMES and path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        suffix = path.suffix.lower()
        if suffix == ".py":
            type_priority = 0
        elif suffix in {".sh", ".bash"}:
            type_priority = 1
        else:
            type_priority = 2
        depth = len(relpath.parts) - 1
        is_entry = relpath.name in SOURCE_ENTRY_NAMES
        candidates.append((type_priority, depth, not is_entry, str(relpath), path))
    candidates.sort()

    total_bytes = 0
    for _type_priority, _depth, _not_entry, relpath_str, path in candidates:
        if len(files) >= MAX_SOURCE_FILES or total_bytes >= MAX_SOURCE_TOTAL_BYTES:
            break
        content = _read_source_file(path)
        remaining = MAX_SOURCE_TOTAL_BYTES - total_bytes
        content = clip_text_bytes(content, remaining)
        content_bytes = len(content.encode("utf-8"))
        if content_bytes == 0:
            continue
        files[relpath_str] = content
        total_bytes += content_bytes
    return files


def collect_code_files(workspace_dir: Path) -> Dict[str, str]:
    """Backward-compatible wrapper for the expanded source collector."""
    return collect_source_files(workspace_dir)
