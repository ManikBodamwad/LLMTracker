"""
LLM model pricing database.
Prices are per 1M tokens in USD. The table is static and bundled with the
package; use ``register_custom_model`` to add or override entries.
Last updated: September 2026

Sources:
- OpenAI: https://openai.com/api/pricing/
- Anthropic: https://www.anthropic.com/pricing
- Google: https://ai.google.dev/pricing
- DeepSeek: https://api-docs.deepseek.com/
- Mistral: https://docs.mistral.ai/
- xAI: https://docs.x.ai/
- Meta / Together / Groq / Fireworks (Llama & Qwen models)
- Cohere: https://cohere.com/pricing
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from llmtrack.pricing.providers import infer_provider

# Structure: model_name -> {"input": price_per_1M, "output": price_per_1M}
# Optional keys "cache_read" / "cache_write" hold absolute prices per 1M
# tokens for cached prompt tokens; when absent, provider defaults apply.
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # --------------------------------------------------------------------------
    # OpenAI Models
    # --------------------------------------------------------------------------
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-2024-11-20": {"input": 2.50, "output": 10.00},
    "gpt-4o-2024-08-06": {"input": 2.50, "output": 10.00},
    "gpt-4o-2024-05-13": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
    "gpt-4.5-preview": {"input": 75.00, "output": 150.00},
    "gpt-4.5": {"input": 75.00, "output": 150.00},
    "chatgpt-4o-latest": {"input": 5.00, "output": 15.00},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-2024-12-17": {"input": 15.00, "output": 60.00},
    "o1-preview": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 1.10, "output": 4.40},
    "o1-mini-2024-09-12": {"input": 1.10, "output": 4.40},
    "o1-pro": {"input": 150.00, "output": 600.00},
    "o3": {"input": 10.00, "output": 40.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    "o4-mini": {"input": 1.10, "output": 4.40},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4-turbo-2024-04-09": {"input": 10.00, "output": 30.00},
    "gpt-4-0125-preview": {"input": 10.00, "output": 30.00},
    "gpt-4-1106-preview": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4-32k": {"input": 60.00, "output": 120.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "gpt-3.5-turbo-0125": {"input": 0.50, "output": 1.50},
    "text-embedding-3-small": {"input": 0.02, "output": 0.00},
    "text-embedding-3-large": {"input": 0.13, "output": 0.00},
    "text-embedding-ada-002": {"input": 0.10, "output": 0.00},
    # --------------------------------------------------------------------------
    # Anthropic Models
    # --------------------------------------------------------------------------
    "claude-3-7-sonnet-20250219": {"input": 3.00, "output": 15.00},
    "claude-3-7-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-opus-5-5": {"input": 4.00, "output": 20.00},
    "claude-sonnet-5": {"input": 2.00, "output": 10.00},
    "claude-fable-5-1": {"input": 10.00, "output": 50.00},
    # --------------------------------------------------------------------------
    # Google Gemini Models
    # --------------------------------------------------------------------------
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.0-flash-001": {"input": 0.10, "output": 0.40},
    "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash-lite-preview-02-05": {"input": 0.075, "output": 0.30},
    "gemini-2.0-pro-exp-02-05": {"input": 1.25, "output": 5.00},
    "gemini-3.8-flash": {"input": 0.75, "output": 3.75},
    "gemini-3.5-flash-lite": {"input": 0.15, "output": 0.60},
    "gemini-3.1-pro-preview": {"input": 2.00, "output": 12.00},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-pro-latest": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash-latest": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash-8b": {"input": 0.0375, "output": 0.15},
    "text-embedding-004": {"input": 0.025, "output": 0.00},
    # --------------------------------------------------------------------------
    # DeepSeek Models
    # --------------------------------------------------------------------------
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    "deepseek-v3": {"input": 0.14, "output": 0.28},
    "deepseek-r1": {"input": 0.55, "output": 2.19},
    "deepseek-v4-flash": {"input": 0.14, "output": 0.28},
    "deepseek-v4-pro": {"input": 1.74, "output": 3.48},
    "deepseek-coder": {"input": 0.14, "output": 0.28},
    # --------------------------------------------------------------------------
    # xAI Grok Models
    # --------------------------------------------------------------------------
    "grok-2": {"input": 2.00, "output": 10.00},
    "grok-2-1212": {"input": 2.00, "output": 10.00},
    "grok-2-latest": {"input": 2.00, "output": 10.00},
    "grok-2-vision": {"input": 2.00, "output": 10.00},
    "grok-2-vision-1212": {"input": 2.00, "output": 10.00},
    "grok-2-vision-latest": {"input": 2.00, "output": 10.00},
    "grok-3": {"input": 3.00, "output": 15.00},
    "grok-3-mini": {"input": 0.30, "output": 1.50},
    "grok-4.7": {"input": 2.00, "output": 6.00},
    "grok-4.6": {"input": 2.00, "output": 6.00},
    "grok-4.1-fast": {"input": 0.20, "output": 0.50},
    "grok-beta": {"input": 5.00, "output": 15.00},
    "grok-vision-beta": {"input": 5.00, "output": 15.00},
    # --------------------------------------------------------------------------
    # Mistral AI Models
    # --------------------------------------------------------------------------
    "mistral-large-2411": {"input": 2.00, "output": 6.00},
    "mistral-large-latest": {"input": 2.00, "output": 6.00},
    "mistral-large": {"input": 2.00, "output": 6.00},
    "mistral-large-3": {"input": 0.50, "output": 1.50},
    "mistral-medium-3.5": {"input": 1.50, "output": 7.50},
    "mistral-medium-latest": {"input": 1.50, "output": 7.50},
    "mistral-small-2409": {"input": 0.10, "output": 0.30},
    "mistral-small-latest": {"input": 0.10, "output": 0.30},
    "mistral-small": {"input": 0.10, "output": 0.30},
    "mistral-small-4": {"input": 0.15, "output": 0.60},
    "codestral-2501": {"input": 0.30, "output": 0.90},
    "codestral-latest": {"input": 0.30, "output": 0.90},
    "codestral": {"input": 0.30, "output": 0.90},
    "pixtral-large-latest": {"input": 2.00, "output": 6.00},
    "pixtral-large": {"input": 2.00, "output": 6.00},
    "pixtral-12b": {"input": 0.15, "output": 0.15},
    "ministral-8b-latest": {"input": 0.10, "output": 0.10},
    "ministral-8b": {"input": 0.10, "output": 0.10},
    "ministral-3b-latest": {"input": 0.04, "output": 0.04},
    "ministral-3b": {"input": 0.04, "output": 0.04},
    "mistral-embed": {"input": 0.10, "output": 0.00},
    # --------------------------------------------------------------------------
    # Meta LLaMA Models (via Provider APIs)
    # --------------------------------------------------------------------------
    "llama-3.3-70b-instruct": {"input": 0.40, "output": 0.40},
    "llama-3.3-70b": {"input": 0.40, "output": 0.40},
    "llama-3.2-90b-vision": {"input": 0.90, "output": 0.90},
    "llama-3.2-11b-vision": {"input": 0.18, "output": 0.18},
    "llama-3.2-3b-instruct": {"input": 0.06, "output": 0.06},
    "llama-3.2-3b": {"input": 0.06, "output": 0.06},
    "llama-3.2-1b-instruct": {"input": 0.04, "output": 0.04},
    "llama-3.2-1b": {"input": 0.04, "output": 0.04},
    "llama-3.1-405b-instruct": {"input": 2.50, "output": 2.50},
    "llama-3.1-405b": {"input": 2.50, "output": 2.50},
    "llama-3.1-70b-instruct": {"input": 0.60, "output": 0.60},
    "llama-3.1-70b": {"input": 0.60, "output": 0.60},
    "llama-3.1-8b-instruct": {"input": 0.10, "output": 0.10},
    "llama-3.1-8b": {"input": 0.10, "output": 0.10},
    # --------------------------------------------------------------------------
    # Alibaba Qwen Models
    # --------------------------------------------------------------------------
    "qwen-2.5-72b-instruct": {"input": 0.35, "output": 0.40},
    "qwen-2.5-72b": {"input": 0.35, "output": 0.40},
    "qwen-2.5-coder-32b-instruct": {"input": 0.20, "output": 0.20},
    "qwen-2.5-coder-32b": {"input": 0.20, "output": 0.20},
    "qwen-2.5-14b-instruct": {"input": 0.15, "output": 0.15},
    "qwen-2.5-14b": {"input": 0.15, "output": 0.15},
    "qwen-2.5-7b-instruct": {"input": 0.08, "output": 0.08},
    "qwen-2.5-7b": {"input": 0.08, "output": 0.08},
    "qwen-max": {"input": 1.60, "output": 6.40},
    "qwen-plus": {"input": 0.40, "output": 1.20},
    "qwen-turbo": {"input": 0.05, "output": 0.20},
    # --------------------------------------------------------------------------
    # Cohere Models
    # --------------------------------------------------------------------------
    "command-r-plus-08-2024": {"input": 2.50, "output": 10.00},
    "command-r-plus": {"input": 2.50, "output": 10.00},
    "command-r-08-2024": {"input": 0.15, "output": 0.60},
    "command-r": {"input": 0.15, "output": 0.60},
    "command-light": {"input": 0.30, "output": 0.60},
    "embed-english-v3.0": {"input": 0.10, "output": 0.00},
    "embed-multilingual-v3.0": {"input": 0.10, "output": 0.00},
}

# Fuzzy match aliases — maps aliases to exact keys
MODEL_ALIASES: Dict[str, str] = {
    # OpenAI
    "gpt4o": "gpt-4o",
    "gpt-4o-latest": "chatgpt-4o-latest",
    "gpt4o-mini": "gpt-4o-mini",
    "gpt-4-turbo-preview": "gpt-4-turbo",
    "o1-preview-latest": "o1-preview",
    # Anthropic
    "claude-3-7": "claude-3-7-sonnet",
    "claude-3.7-sonnet": "claude-3-7-sonnet",
    "claude-3.5-sonnet": "claude-3-5-sonnet",
    "claude-3.5-haiku": "claude-3-5-haiku",
    "claude-3.0-opus": "claude-3-opus",
    "claude-3.0-haiku": "claude-3-haiku",
    "claude-sonnet-latest": "claude-3-7-sonnet",
    "claude-haiku-latest": "claude-3-5-haiku",
    "claude-opus-latest": "claude-3-opus",
    # Google
    "gemini-flash": "gemini-2.0-flash",
    "gemini-pro": "gemini-2.5-pro",
    "gemini-2-flash": "gemini-2.0-flash",
    "gemini-2-flash-lite": "gemini-2.0-flash-lite",
    "gemini-1.5-flash-8b-latest": "gemini-1.5-flash-8b",
    # DeepSeek
    "r1": "deepseek-r1",
    "v3": "deepseek-v3",
    "deepseek-reasoner-latest": "deepseek-r1",
    "deepseek-chat-latest": "deepseek-v3",
    # xAI
    "grok": "grok-2",
    "grok-2-vision-preview": "grok-2-vision",
    # Meta
    "llama-70b": "llama-3.3-70b",
    "llama-8b": "llama-3.1-8b",
    "llama-405b": "llama-3.1-405b",
    "llama3": "llama-3.3-70b",
    "llama3.3": "llama-3.3-70b",
    # Qwen
    "qwen": "qwen-2.5-72b",
    "qwen-coder": "qwen-2.5-coder-32b",
}

# Fallback pricing when model is unknown ($1.00 in, $3.00 out per 1M tokens)
FALLBACK_PRICING: Dict[str, float] = {"input": 1.00, "output": 3.00}


# Cached prompt-token price as a multiple of the base input price, per provider.
# (cache_read_multiplier, cache_write_multiplier). Providers not listed are
# billed at the full input price, which can only over-estimate.
CACHE_MULTIPLIERS: Dict[str, Tuple[float, float]] = {
    "anthropic": (0.10, 1.25),
    "openai": (0.50, 1.00),
    "google": (0.25, 1.00),
    "deepseek": (0.10, 1.00),
}


@dataclass(frozen=True)
class CostEstimate:
    """Result of a cost calculation."""

    cost_usd: float
    #: True when the price came from fuzzy matching or the fallback rate rather
    #: than an exact/alias/normalized table entry.
    estimated: bool


def get_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    """
    Calculate cost for a given model and token counts.

    Args:
        model: Model name string (e.g. "gpt-4o", "claude-3-7-sonnet", "deepseek-r1")
        input_tokens: Total number of input/prompt tokens, *including* any
            cached and cache-creation tokens.
        output_tokens: Number of output/completion tokens
        cached_input_tokens: Portion of ``input_tokens`` served from a prompt cache.
        cache_creation_tokens: Portion of ``input_tokens`` written to a prompt cache.

    Returns:
        Cost in USD as float rounded to 8 decimal places.
    """
    return estimate_cost(
        model,
        input_tokens,
        output_tokens,
        cached_input_tokens=cached_input_tokens,
        cache_creation_tokens=cache_creation_tokens,
    ).cost_usd


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> CostEstimate:
    """Like :func:`get_cost`, but also reports whether the price was estimated."""
    pricing, source = resolve_pricing(model)

    cached = max(0, min(cached_input_tokens, input_tokens))
    created = max(0, min(cache_creation_tokens, input_tokens - cached))
    regular = input_tokens - cached - created

    read_mult, write_mult = CACHE_MULTIPLIERS.get(infer_provider(model), (1.0, 1.0))
    read_price = pricing.get("cache_read", pricing["input"] * read_mult)
    write_price = pricing.get("cache_write", pricing["input"] * write_mult)

    input_cost = (
        regular * pricing["input"] + cached * read_price + created * write_price
    ) / 1_000_000
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return CostEstimate(
        cost_usd=round(input_cost + output_cost, 8),
        estimated=source in ("fuzzy", "fallback"),
    )


def resolve_pricing(model: str) -> Tuple[Dict[str, float], str]:
    """
    Resolve a model name to ``(pricing, source)``.

    ``source`` is one of ``"exact"``, ``"alias"``, ``"normalized"`` (case or
    vendor-prefix differences only), ``"fuzzy"`` (a known model name appears in
    the string as a whole token) or ``"fallback"`` (unknown model).
    """
    if not model or not isinstance(model, str):
        return FALLBACK_PRICING, "fallback"

    if model in MODEL_PRICING:
        return MODEL_PRICING[model], "exact"
    if model in MODEL_ALIASES and MODEL_ALIASES[model] in MODEL_PRICING:
        return MODEL_PRICING[MODEL_ALIASES[model]], "alias"

    model_lower = model.lower().strip()
    candidates = [model_lower]
    if "/" in model_lower:
        candidates.append(model_lower.rsplit("/", 1)[-1])

    lowered_pricing = {k.lower(): v for k, v in MODEL_PRICING.items()}
    lowered_aliases = {k.lower(): v for k, v in MODEL_ALIASES.items()}
    for name in candidates:
        if name in lowered_pricing:
            return lowered_pricing[name], "normalized"
        target = lowered_aliases.get(name)
        if target in MODEL_PRICING:
            return MODEL_PRICING[target], "normalized"

    # Fuzzy: longest known model name that appears as a whole token, e.g.
    # "claude-3-5-sonnet-20241022-v2:0" or "us.anthropic.claude-3-5-haiku-x".
    # Deliberately NOT bidirectional: "gpt-4.1" must not match "gpt-4".
    for key in sorted(MODEL_PRICING, key=len, reverse=True):
        if _contains_token(model_lower, key.lower()):
            return MODEL_PRICING[key], "fuzzy"

    return FALLBACK_PRICING, "fallback"


def _resolve_pricing(model: str) -> Dict[str, float]:
    """Resolve model name to a pricing dict (see :func:`resolve_pricing`)."""
    return resolve_pricing(model)[0]


def _contains_token(haystack: str, needle: str) -> bool:
    """True if ``needle`` occurs in ``haystack`` delimited by non-alphanumerics."""
    start = 0
    while True:
        i = haystack.find(needle, start)
        if i < 0:
            return False
        j = i + len(needle)
        before_ok = i == 0 or not haystack[i - 1].isalnum()
        after_ok = j == len(haystack) or (
            not haystack[j].isalnum() and haystack[j] != "."
        )
        if before_ok and after_ok:
            return True
        start = i + 1


def list_models() -> List[str]:
    """Return all supported model names."""
    return sorted(MODEL_PRICING.keys())
