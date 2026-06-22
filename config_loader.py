from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, Set

import yaml


def load_yaml_config(config_path: str | None) -> Dict[str, Any]:
    if not config_path:
        return {}
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config file must contain a mapping at the top level: {path}")
    return raw


def merge_args_with_config(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    config: Dict[str, Any],
    section: str | None = None,
    explicit_keys: Set[str] | None = None,
) -> argparse.Namespace:
    if not config:
        return args

    scoped_config = config.get(section, config) if section else config

    if not isinstance(scoped_config, dict):
        raise ValueError("Config section must be a mapping.")

    explicit_keys = explicit_keys or set()

    for key, value in scoped_config.items():
        if key == "config":
            continue
        if not hasattr(args, key):
            continue
        if key in explicit_keys:
            continue
        default = parser.get_default(key)
        current = getattr(args, key)
        if current == default or current is None:
            setattr(args, key, value)
    return args
