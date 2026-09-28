"""
Provider inference from model identifiers.
"""

from __future__ import annotations

import re

# Explicit vendor prefixes used by LiteLLM-style model strings ("openai/gpt-4o").
_PREFIX_TO_PROVIDER = {
    "openai": "openai",
    "azure": "openai",
    "anthropic": "anthropic",
    "gemini": "google",
    "vertex_ai": "google",
    "google": "google",
    "xai": "xai",
    "deepseek": "deepseek",
    "mistral": "mistral",
    "cohere": "cohere",
}

# OpenAI reasoning models: o1, o3-mini, o4-mini, ...
_O_SERIES = re.compile(r"^o\d(?![a-z0-9])")


def infer_provider(model: str) -> str:
    """Infer provider name from a model string."""
    model_lower = (model or "").lower().strip()

    if "/" in model_lower:
        prefix, _, model_lower = model_lower.partition("/")
        if prefix in _PREFIX_TO_PROVIDER:
            return _PREFIX_TO_PROVIDER[prefix]
        model_lower = model_lower.rsplit("/", 1)[-1]

    if _O_SERIES.match(model_lower) or any(
        x in model_lower for x in ("gpt", "chatgpt", "text-davinci", "text-embedding")
    ):
        return "openai"
    if "claude" in model_lower:
        return "anthropic"
    if "gemini" in model_lower:
        return "google"
    if "grok" in model_lower:
        return "xai"
    if "deepseek" in model_lower:
        return "deepseek"
    if any(
        x in model_lower
        for x in ("mistral", "mixtral", "codestral", "ministral", "pixtral")
    ):
        return "mistral"
    if any(x in model_lower for x in ("command", "cohere", "embed-")):
        return "cohere"
    if "qwen" in model_lower:
        return "alibaba"
    if "llama" in model_lower:
        return "meta"
    return "other"
