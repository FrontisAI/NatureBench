"""Backend factories for NatureBench agents."""

from .base_backend import LLMBackend
from .openai_backend import OpenAIBackend

__all__ = ["LLMBackend", "OpenAIBackend"]

