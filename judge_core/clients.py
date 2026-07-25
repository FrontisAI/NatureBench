"""Provider configuration and HTTP clients for the validity judge."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, List, Optional, Tuple

from judge_core.policy import (
    DEFAULT_ANTHROPIC_BASE_URL,
    DEFAULT_JUDGE_MODEL,
    DEFAULT_OPENAI_BASE_URL,
    DEFAULT_TIMEOUT,
    JUDGE_SYSTEM,
    MAX_JUDGE_OUTPUT_TOKENS,
)


def _first_nonempty(*values: Optional[str]) -> Optional[str]:
    """Return the first non-empty configuration value."""
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _provider_for_model(model: str) -> str:
    """Select OpenAI Responses for gpt-* models, Anthropic otherwise."""
    return "openai" if model.lower().startswith("gpt-") else "anthropic"


def resolve_judge_config(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    *,
    provider: Optional[str] = None,
) -> Tuple[str, str, str, Optional[str]]:
    """Resolve the provider, model, base URL, and API key at call time."""
    resolved_model = _first_nonempty(
        model,
        os.environ.get("JUDGE_MODEL"),
        DEFAULT_JUDGE_MODEL,
    ) or DEFAULT_JUDGE_MODEL
    resolved_provider = provider or _provider_for_model(resolved_model)
    if resolved_provider == "openai":
        resolved_base_url = _first_nonempty(
            base_url,
            os.environ.get("JUDGE_OPENAI_BASE_URL"),
            os.environ.get("JUDGE_BASE_URL"),
            DEFAULT_OPENAI_BASE_URL,
        ) or DEFAULT_OPENAI_BASE_URL
        resolved_api_key = _first_nonempty(
            api_key,
            os.environ.get("JUDGE_OPENAI_API_KEY"),
            os.environ.get("JUDGE_API_KEY"),
        )
    else:
        resolved_base_url = _first_nonempty(
            base_url,
            os.environ.get("JUDGE_ANTHROPIC_BASE_URL"),
            os.environ.get("JUDGE_BASE_URL"),
            os.environ.get("ANTHROPIC_BASE_URL"),
            DEFAULT_ANTHROPIC_BASE_URL,
        ) or DEFAULT_ANTHROPIC_BASE_URL
        resolved_api_key = _first_nonempty(
            api_key,
            os.environ.get("JUDGE_ANTHROPIC_API_KEY"),
            os.environ.get("JUDGE_API_KEY"),
            os.environ.get("ANTHROPIC_API_KEY"),
        )
    return resolved_provider, resolved_model, resolved_base_url, resolved_api_key


def build_api_url(base_url: str, endpoint: str) -> str:
    """Append an API endpoint without duplicating a terminal /v1 prefix."""
    normalized_base = base_url.strip().rstrip("/")
    if normalized_base.endswith(endpoint):
        return normalized_base
    if normalized_base.endswith("/v1"):
        return normalized_base + endpoint[len("/v1") :]
    return normalized_base + endpoint


def _http_error_message(error: urllib.error.HTTPError) -> str:
    """Return a bounded HTTP error category without request or response data."""
    return f"HTTP {error.code}: request failed"


def _network_error_message() -> str:
    """Return a generic network category without configured endpoint details."""
    return "network error: request failed"


def call_anthropic_judge(
    user_prompt: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Tuple[bool, str]:
    """Call the Anthropic Messages API once and return raw text or an error."""
    _, resolved_model, resolved_base_url, resolved_api_key = resolve_judge_config(
        model,
        base_url,
        api_key,
        provider="anthropic",
    )
    if not resolved_api_key:
        return (
            False,
            "no API key (set JUDGE_ANTHROPIC_API_KEY, JUDGE_API_KEY, "
            "or ANTHROPIC_API_KEY)",
        )
    url = build_api_url(resolved_base_url, "/v1/messages")
    body = {
        "model": resolved_model,
        "max_tokens": MAX_JUDGE_OUTPUT_TOKENS,
        "system": JUDGE_SYSTEM,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": resolved_api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload: Any = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return False, _http_error_message(error)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return False, f"invalid JSON response: {error}"
    except (urllib.error.URLError, OSError):
        return False, _network_error_message()

    content = payload.get("content", []) if isinstance(payload, dict) else []
    text_parts: List[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text_parts.append(str(block.get("text", "")))
    return True, "".join(text_parts)


def call_openai_judge(
    user_prompt: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Tuple[bool, str]:
    """Call the OpenAI Responses API once and return raw text or an error."""
    _, resolved_model, resolved_base_url, resolved_api_key = resolve_judge_config(
        model,
        base_url,
        api_key,
        provider="openai",
    )
    if not resolved_api_key:
        return False, "no API key (set JUDGE_OPENAI_API_KEY or JUDGE_API_KEY)"
    url = build_api_url(resolved_base_url, "/v1/responses")
    body = {
        "model": resolved_model,
        "instructions": JUDGE_SYSTEM,
        "input": user_prompt,
        "max_output_tokens": MAX_JUDGE_OUTPUT_TOKENS,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {resolved_api_key}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload: Any = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return False, _http_error_message(error)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return False, f"invalid JSON response: {error}"
    except (urllib.error.URLError, OSError):
        return False, _network_error_message()

    output = payload.get("output", []) if isinstance(payload, dict) else []
    text_parts: List[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        for block in item.get("content", []):
            if isinstance(block, dict) and block.get("type") == "output_text":
                text_parts.append(str(block.get("text", "")))
    return True, "".join(text_parts)


def call_judge(
    user_prompt: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Tuple[bool, str]:
    """Dispatch one judge call according to the resolved model family."""
    provider, resolved_model, resolved_base_url, resolved_api_key = (
        resolve_judge_config(model, base_url, api_key)
    )
    call = call_openai_judge if provider == "openai" else call_anthropic_judge
    return call(
        user_prompt,
        model=resolved_model,
        base_url=resolved_base_url,
        api_key=resolved_api_key,
        timeout=timeout,
    )
