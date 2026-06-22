"""Quick smoke-test for NatureBench LLM backend wiring.

Usage:
    python -m agent.check_llm_backend --model gpt-4o-mini --prompt "Hello!"

This script sends a single message through `LLMBackend` and prints the raw
model response together with token statistics.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict

from .backend.base_backend import LLMBackend


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test the NatureBench LLM backend.")
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="Model name passed to LLMBackend (default: %(default)s).",
    )
    parser.add_argument(
        "--prompt",
        default="Say hello from NatureBench.",
        help="User message sent to the model.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature forwarded to the LLM.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=0.95,
        help="Top-p nucleus sampling parameter.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum completion tokens to request.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Explicit API key (otherwise reads OPENAI_API_KEY from env).",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Optional base URL if using a compatible proxy endpoint.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Request timeout passed to the SDK.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum automatic retries handled by the SDK.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Missing API key. Provide --api-key or set OPENAI_API_KEY.")

    backend = LLMBackend(
        args.model,
        api_key=api_key,
        base_url=args.base_url,
        timeout=args.timeout,
        max_retries=args.max_retries,
    )

    messages: List[Dict[str, str]] = [{"role": "user", "content": args.prompt}]
    content, prompt_tokens, completion_tokens = backend.respond(
        messages,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
    )

    print("=" * 80)
    print(f"Model reply:\n{content}")
    print("=" * 80)
    print(f"Prompt tokens: {prompt_tokens}")
    print(f"Completion tokens: {completion_tokens}")


if __name__ == "__main__":
    main()

