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
