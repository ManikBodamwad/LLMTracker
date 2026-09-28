"""
Pricing updater module for dynamic model registration and updates.
"""

from typing import Dict, List, Optional

from llmtrack.pricing.models import MODEL_ALIASES, MODEL_PRICING


def register_custom_model(
    model: str,
    input_price_per_1m: float,
    output_price_per_1m: float,
    aliases: Optional[List[str]] = None,
    cache_read_price_per_1m: Optional[float] = None,
    cache_write_price_per_1m: Optional[float] = None,
) -> None:
    """
    Register or update pricing for a custom/new model.

    Args:
        model: Unique identifier of the model.
        input_price_per_1m: Price in USD per 1M input tokens.
        output_price_per_1m: Price in USD per 1M output tokens.
        aliases: Optional list of alias strings for fuzzy matching.
        cache_read_price_per_1m: Optional price per 1M cached prompt tokens read.
            Defaults to the provider's usual discount (or the input price).
        cache_write_price_per_1m: Optional price per 1M prompt tokens written
            to a cache.
    """
    pricing: Dict[str, float] = {
        "input": float(input_price_per_1m),
        "output": float(output_price_per_1m),
    }
    if cache_read_price_per_1m is not None:
        pricing["cache_read"] = float(cache_read_price_per_1m)
    if cache_write_price_per_1m is not None:
        pricing["cache_write"] = float(cache_write_price_per_1m)
    MODEL_PRICING[model] = pricing
    if aliases:
        for alias in aliases:
            MODEL_ALIASES[alias] = model
