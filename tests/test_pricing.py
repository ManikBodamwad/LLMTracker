from llmtrack.pricing.models import (
    FALLBACK_PRICING,
    get_cost,
    list_models,
)
from llmtrack.pricing.updater import register_custom_model


def test_get_cost_known_models():
    # gpt-4o: $2.50 / 1M input, $10.00 / 1M output
    cost = get_cost("gpt-4o", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == 12.50

    # gpt-4o-mini: $0.15 / 1M in, $0.60 / 1M out
    cost_mini = get_cost("gpt-4o-mini", input_tokens=1_000, output_tokens=1_000)
    expected_mini = round((1000 / 1e6) * 0.15 + (1000 / 1e6) * 0.60, 8)
    assert cost_mini == expected_mini


def test_get_cost_aliases():
    # claude-3-5-sonnet should resolve to claude-3-5-sonnet-20241022
    cost_alias = get_cost("claude-3-5-sonnet", input_tokens=1000, output_tokens=1000)
    cost_exact = get_cost(
        "claude-3-5-sonnet-20241022", input_tokens=1000, output_tokens=1000
    )
    assert cost_alias == cost_exact


def test_get_cost_fallback_for_unknown():
    cost_unknown = get_cost(
        "unknown-model-xyz", input_tokens=1_000_000, output_tokens=1_000_000
    )
    assert cost_unknown == FALLBACK_PRICING["input"] + FALLBACK_PRICING["output"]


def test_get_cost_zero_tokens():
    assert get_cost("gpt-4o", input_tokens=0, output_tokens=0) == 0.0


def test_list_models():
    models = list_models()
    assert isinstance(models, list)
    assert len(models) >= 20
    assert "gpt-4o" in models
    assert "claude-sonnet-4-5" in models


def test_register_custom_model():
    register_custom_model(
        model="custom-enterprise-llm",
        input_price_per_1m=5.0,
        output_price_per_1m=20.0,
        aliases=["enterprise-llm-alias"],
    )
    cost = get_cost(
        "custom-enterprise-llm", input_tokens=1_000_000, output_tokens=1_000_000
    )
    assert cost == 25.0

    cost_alias = get_cost(
        "enterprise-llm-alias", input_tokens=1_000_000, output_tokens=1_000_000
    )
    assert cost_alias == 25.0


def test_resolve_pricing_sources():
    from llmtrack.pricing.models import resolve_pricing

    assert resolve_pricing("gpt-4o")[1] == "exact"
    assert resolve_pricing("gpt4o")[1] == "alias"
    assert resolve_pricing("GPT-4o")[1] == "normalized"
    assert resolve_pricing("openai/gpt-4o")[1] == "normalized"
    assert resolve_pricing("claude-3-5-sonnet-20241022-v2:0")[1] == "fuzzy"
    assert resolve_pricing("us.anthropic.claude-3-5-haiku-20241022-v1:0")[1] == "fuzzy"
    assert resolve_pricing("nope")[1] == "fallback"


def test_fuzzy_matching_does_not_guess_from_fragments():
    from llmtrack.pricing.models import resolve_pricing

    # A newer minor version must not silently take an older model's price...
    assert resolve_pricing("gpt-4.99-mini")[1] == "fallback"
    # ...and short model names must not match inside unrelated strings.
    assert resolve_pricing("foo1bar")[1] == "fallback"
    assert resolve_pricing("gpt")[1] == "fallback"


def test_custom_cache_prices():
    from llmtrack.pricing.models import estimate_cost

    register_custom_model("cache-priced-llm", 10.0, 20.0, cache_read_price_per_1m=1.0)
    est = estimate_cost("cache-priced-llm", 1_000_000, 0, cached_input_tokens=1_000_000)
    assert est.cost_usd == 1.0
    assert est.estimated is False
