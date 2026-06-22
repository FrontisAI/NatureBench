"""NatureBench agent package.

This module exposes the default agents so that callers can import them
without needing to know the underlying file structure.
"""

from .base import BaseAgent
from .dummy import DummyAgent
from .codex import CodexAgent
from .claude import ClaudeAgent
from .gemini import GeminiAgent

__all__ = ["BaseAgent", "DummyAgent", "CodexAgent", "ClaudeAgent", "GeminiAgent"]

