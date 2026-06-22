from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class EvaluatorError(Exception):
    """Base exception for evaluator related failures."""


@dataclass
class TaskScore:
    """Structured container for a single task evaluation."""

    task_name: str
    score: Optional[float]
    higher_is_better: Optional[bool]
    metric_name: Optional[str]
    status: str
    message: str

