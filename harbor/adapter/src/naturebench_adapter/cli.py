from __future__ import annotations

import argparse
from pathlib import Path

from .adapter import convert_task


def discover_tasks(source_root: Path) -> dict[str, Path]:
    tasks: dict[str, Path] = {}
    if not source_root.is_dir():
        raise FileNotFoundError(source_root)
    for child in sorted(source_root.iterdir()):
        if child.is_dir() and (child / "metadata.json").is_file():
            tasks[child.name] = child
    return tasks


def rendered_task_ids(output_dir: Path) -> list[str]:
    if not output_dir.is_dir():
        return []
    return sorted(
        child.name
        for child in output_dir.iterdir()
        if child.is_dir() and (child / "task.toml").is_file()
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert NatureBench tasks to Harbor")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--task-ids", nargs="*")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    discovered = discover_tasks(args.source_root)
    selected = args.task_ids if args.task_ids else sorted(discovered)
    if args.limit is not None:
        if args.limit < 0:
            raise ValueError("--limit must be non-negative")
        selected = selected[: args.limit]
    missing = [task_id for task_id in selected if task_id not in discovered]
    if missing:
        raise ValueError("unknown task ids: " + ", ".join(missing))
    converted = []
    for task_id in selected:
        convert_task(discovered[task_id], args.output_dir, overwrite=args.overwrite)
        converted.append(task_id)
        print(f"converted {task_id}")
    all_rendered = rendered_task_ids(args.output_dir)
    print(
        f"converted {len(converted)} task(s); "
        f"output now contains {len(all_rendered)} task(s) in {args.output_dir}"
    )


if __name__ == "__main__":
    main()
