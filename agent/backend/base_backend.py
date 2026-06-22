"""Shared backend factory."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


class LLMBackend:
    """Factory that dispatches to a concrete backend implementation."""

    def __init__(self, backend_name: str, **backend_kwargs: Any) -> None:
        self.backend_name = backend_name
        self._backend = self._initialize_backend(backend_name, backend_kwargs)

    def _initialize_backend(self, backend_name: str, backend_kwargs: Dict[str, Any]):
        if backend_name.startswith(("gpt", "claude", "deepseek")):
            from .openai_backend import OpenAIBackend

            return OpenAIBackend(backend_name, **backend_kwargs)

        raise ValueError(f"Unsupported backend '{backend_name}'.")

    def respond(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> Tuple[str, int, int]:
        return self._backend.respond(
            messages,
            **kwargs,
        )

