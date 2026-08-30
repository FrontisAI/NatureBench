from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
_RANGE_RE = re.compile(
    r"^\s*~?\s*([-+]?\d+(?:\.\d+)?)\s*(?:to|-|–|—)\s*~?\s*([-+]?\d+(?:\.\d+)?)\s*$"
)
_BOUND_RE = re.compile(r"^[<>]=?\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)")
_MEAN_RE = re.compile(
    r"\bmean\s*=\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", re.IGNORECASE
)


def _parse_one_score(value: Any, higher_is_better: bool) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    explicit = _MEAN_RE.search(text)
    if explicit:
        return float(explicit.group(1))
    core = text.split("(")[0].strip().lstrip("~").strip()
    match = _RANGE_RE.match(core)
    if match:
        low, high = float(match.group(1)), float(match.group(2))
        return high if higher_is_better else low
    match = _BOUND_RE.match(core)
    if match:
        return float(match.group(1))
    if "±" in core:
        core = core.split("±", 1)[0].strip().lstrip("~").strip()
    match = _NUM_RE.match(core)
    return float(match.group(0)) if match else None


def _best_sota(value: Any, higher_is_better: bool) -> float | None:
    items = value if isinstance(value, list) else [value]
    parsed = []
    for item in items:
        candidate = item.get("value") if isinstance(item, dict) else item
        number = _parse_one_score(candidate, higher_is_better)
        if number is not None:
            parsed.append(number)
    if not parsed:
        return None
    return max(parsed) if higher_is_better else min(parsed)


def load_primary_table(metadata_path: Path) -> dict[str, dict[str, Any]]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    table: dict[str, dict[str, Any]] = {}
    for entry in metadata.get("performance_entries", []):
        instance = entry.get("dataset_name") or entry.get("instance_name")
        primary = next(
            (metric for metric in entry.get("metrics", []) if metric.get("is_primary")),
            None,
        )
        if not instance or not primary or not primary.get("name"):
            continue
        higher = primary.get("metric_direction") == "higher_is_better"
        sota = _best_sota(primary.get("sota_score"), higher)
        if sota in (None, 0):
            continue
        table[instance] = {
            "metric": primary["name"],
            "higher_is_better": higher,
            "sota": sota,
        }
    if not table:
        raise ValueError(f"no usable primary metrics in {metadata_path}")
    return table


def _find_metric_value(scores: Any, target_metric: str) -> float | None:
    normalize = lambda value: str(value).lower().replace("_", "").replace(" ", "").replace("-", "")
    target = normalize(target_metric)
    if not isinstance(scores, dict):
        return None
    for key, value in scores.items():
        if normalize(key) == target and isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    for value in scores.values():
        nested = _find_metric_value(value, target_metric)
        if nested is not None:
            return nested
    return None


def compute_improvements(
    raw_scores: dict[str, Any], primary_table: dict[str, dict[str, Any]]
) -> tuple[dict[str, float], float | None]:
    per_instance: dict[str, float] = {}
    for instance, info in primary_table.items():
        block = raw_scores.get(instance) if isinstance(raw_scores, dict) else None
        score = _find_metric_value(block, info["metric"])
        if score is None or not math.isfinite(score):
            per_instance[instance] = -1.0
            continue
        direction = 1.0 if info["higher_is_better"] else -1.0
        per_instance[instance] = direction * (score - info["sota"]) / abs(info["sota"])
    if not per_instance:
        return {}, None
    return per_instance, sum(per_instance.values()) / len(per_instance)
