#!/usr/bin/env python3
"""Prepare metadata, result rows, and a task list for any NatureBench track."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable

import yaml

from validate_submission import (
    SUPPORTED_TRACKS,
    RESULT_FIELDS,
    default_case_metadata_path,
    load_track_case_metadata,
)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", choices=SUPPORTED_TRACKS, default="full")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        cases = load_track_case_metadata(default_case_metadata_path(), args.track)
        root = args.output_dir
        paths = [root / name for name in ("submission.yaml", "results.csv", "tasks.txt")]
        existing = [str(path) for path in paths if path.exists()]
        if existing:
            raise ValueError("refusing to overwrite existing files: " + ", ".join(existing))
        template = Path(__file__).with_name("templates") / "submission.yaml"
        metadata = yaml.safe_load(template.read_text(encoding="utf-8"))
        metadata["evaluation"]["track"] = args.track
        root.mkdir(parents=True, exist_ok=True)
        with paths[0].open("x", encoding="utf-8") as handle:
            yaml.safe_dump(metadata, handle, sort_keys=False, allow_unicode=True)
        with paths[1].open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
            writer.writeheader()
            writer.writerows({"case_id": case_id} for case_id in cases)
        with paths[2].open("x", encoding="utf-8") as handle:
            handle.write("\n".join(cases) + "\n")
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Prepared {args.track}: {len(cases)} tasks in {root}. Complete submission.yaml and results.csv after evaluation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
