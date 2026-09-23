"""
Pricing updater module for dynamic model registration and updates.
"""

from typing import Optional

from llmtrack.pricing.models import MODEL_ALIASES, MODEL_PRICING


def register_custom_model(
    model: str,
    input_price_per_1m: float,
    output_price_per_1m: float,
    aliases: Optional[list[str]] = None,
) -> None:
    """
    Register or update pricing for a custom/new model.

    Args:
        model: Unique identifier of the model.
        input_price_per_1m: Price in USD per 1M input tokens.
        output_price_per_1m: Price in USD per 1M output tokens.
        aliases: Optional list of alias strings for fuzzy matching.
    """
    MODEL_PRICING[model] = {
        "input": float(input_price_per_1m),
        "output": float(output_price_per_1m),
    }
    if aliases:
        for alias in aliases:
            MODEL_ALIASES[alias] = model
