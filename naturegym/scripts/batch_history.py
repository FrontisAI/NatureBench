#!/usr/bin/env python3
"""Move previous outputs to a shared numeric suffix before a sequential rerun.

Only pass outputs replaced by this action, never its inputs or shared state.
Current filenames remain the interface used by downstream stages.
"""

from pathlib import Path
import os
import re
import sys
from typing import Dict, Union


def archive_outputs(*filenames: Union[str, Path]) -> Dict[Path, Path]:
    """Archive existing files as stem.N.suffix; never overwrite an archive.

    A group uses max(existing group numbers) + 1, including log-only failures.
    All archive links are created before removing current names, so a link
    failure leaves current outputs intact. Calls for one target are sequential.
    """
    paths = list(dict.fromkeys(Path(name).absolute() for name in filenames))
    current = []
    number = 0
    for path in paths:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError(f"Expected a regular output file: {path}")
        if path.is_file():
            current.append(path)
        pattern = re.compile(re.escape(path.stem) + r"\.([1-9][0-9]*)" + re.escape(path.suffix))
        if path.parent.is_dir():
            for entry in path.parent.iterdir():
                match = pattern.fullmatch(entry.name)
                if match:
                    number = max(number, int(match[1]))
    archived = {path: path.with_name(f"{path.stem}.{number + 1}{path.suffix}")
                for path in current}
    created = []
    try:
        for source, destination in archived.items():
            # Exclusive creation: unlike rename(), link() cannot replace history.
            os.link(source, destination)
            created.append(destination)
    except OSError:
        for destination in created:
            destination.unlink()
        raise
    for source, destination in archived.items():
        source.unlink()
        print(f"Archived: {source} -> {destination}", flush=True)
    return archived


if __name__ == "__main__":
    archive_outputs(*sys.argv[1:])
