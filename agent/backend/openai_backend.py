"""OpenAI-style backend using the official SDK."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

import backoff
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)


def _default_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if not messages:
        raise ValueError("messages must contain at least one entry.")
    return messages


def _message_content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence):
        parts: List[str] = []
        for part in content:
            text = getattr(part, "text", None)
            if text is None and isinstance(part, dict):
                text = part.get("text")
            parts.append(text or "")
        return "".join(parts)
    return str(content)


@backoff.on_exception(
    backoff.expo,
    (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError),
    max_time=120,
)
def _create_chat_completion(client: OpenAI, **kwargs: Any):
    return client.chat.completions.create(**kwargs)


class OpenAIBackend:
    """Thin wrapper around the OpenAI Chat Completions API.
    
    API credentials are read from environment variables:
    - OPENAI_API_KEY: API key for authentication
    - OPENAI_BASE_URL: Custom base URL (optional)
    """

    def __init__(
        self,
        model_name: str,
        *,
        timeout: float = 120.0,
        max_retries: int = 10,
    ) -> None:
        self.model_name = model_name
        self.client = OpenAI(timeout=timeout, max_retries=max_retries)

    def respond(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> Tuple[str, int, int]:
        extra = dict(kwargs)
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": _default_messages(messages),
        }
        payload.update(extra)

        response = _create_chat_completion(self.client, **payload)
        choice = response.choices[0]
        content = _message_content_to_text(choice.message.content)

        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        return content, prompt_tokens, completion_tokens

