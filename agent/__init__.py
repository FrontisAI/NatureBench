"""NatureBench agent package.

This module exposes the default agents so that callers can import them
without needing to know the underlying file structure.
"""

from .base import BaseAgent
from .dummy import DummyAgent
from .codex import CodexAgent
from .claude import ClaudeAgent
from .gemini import GeminiAgent
from . import lumen_adapter  # noqa: F401  (registers the Lumen adapter on import)

__all__ = ["BaseAgent", "DummyAgent", "CodexAgent", "ClaudeAgent", "GeminiAgent"]

