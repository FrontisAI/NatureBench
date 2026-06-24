#!/usr/bin/env python3
"""
Shared target selection helpers for batch scripts.
"""

from __future__ import annotations

import argparse
import os
import re
from typing import List, Optional, Tuple, Union


def natural_sort_key(name: str) -> Tuple[Union[int, str], ...]:
    """Sort key: numeric substrings compare as integers (matches typical file managers)."""
    parts = re.split(r"(\d+)", name)
    key: List[Union[int, str]] = []
    for p in parts:
        if p == "":
            continue
        key.append(int(p) if p.isdigit() else p.lower())
    return tuple(key)


def add_target_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common target selection arguments to a batch parser."""
    parser.add_argument(
        "path",
        help="Parent directory to scan, or a single folder when used with --single",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Process only the specified folder itself instead of its subfolders",
    )
    parser.add_argument(
        "--start",
        type=int,
        metavar="N",
        help="Start from the Nth subfolder (1-based, inclusive) under the parent directory",
    )
    parser.add_argument(
        "--end",
        type=int,
        metavar="N",
        help="End at the Nth subfolder (1-based, inclusive) under the parent directory",
    )
    parser.add_argument(
        "--sort",
        choices=("natural", "lexical"),
        default="natural",
        help=(
            "Order of subfolders for --start/--end: natural (digits as numbers, like many file "
            "managers) or lexical (plain string sort)"
        ),
    )


def resolve_targets(
    path: str,
    *,
    single: bool = False,
    start: Optional[int] = None,
    end: Optional[int] = None,
    sort: str = "natural",
) -> Tuple[List[str], str]:
    """
    Resolve targets from a single folder or a subfolder range.

    Returns:
        Tuple of (selected_targets, selection_summary)
    """
    if not os.path.isdir(path):
        raise ValueError(f"'{path}' is not a valid directory!")

    normalized_path = os.path.abspath(path)

    if single:
        if start is not None or end is not None:
            raise ValueError("--single cannot be used together with --start/--end")
        return [normalized_path], f"Single folder: {normalized_path}"

    names = [
        n for n in os.listdir(normalized_path) if os.path.isdir(os.path.join(normalized_path, n))
    ]
    if sort == "lexical":
        names.sort()
    elif sort == "natural":
        names.sort(key=natural_sort_key)
    else:
        raise ValueError(f"Unknown sort mode: {sort!r}")

    subfolders = [os.path.join(normalized_path, item) for item in names]

    if not subfolders:
        raise ValueError(f"No subfolders found in '{path}'")

    total = len(subfolders)
    start_idx = 1 if start is None else start
    end_idx = total if end is None else end

    if start_idx < 1 or end_idx < 1:
        raise ValueError("--start and --end must be positive integers")
    if start_idx > end_idx:
        raise ValueError("--start cannot be greater than --end")
    if start_idx > total:
        raise ValueError(
            f"--start={start_idx} exceeds subfolder count ({total}) in '{path}'"
        )
    if end_idx > total:
        raise ValueError(
            f"--end={end_idx} exceeds subfolder count ({total}) in '{path}'"
        )

    selected = subfolders[start_idx - 1 : end_idx]
    summary = (
        f"Parent folder: {normalized_path} (subfolders {start_idx}-{end_idx} of {total}, sort={sort})"
    )
    return selected, summary
