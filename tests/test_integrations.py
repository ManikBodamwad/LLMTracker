from unittest.mock import MagicMock

import anthropic
import litellm
import openai

from llmtrack import CostTracker, feature
from llmtrack.integrations.anthropic import patch_anthropic
from llmtrack.integrations.litellm import patch_litellm
from llmtrack.integrations.openai import patch_openai
from llmtrack.pricing.models import FALLBACK_PRICING, _resolve_pricing
from llmtrack.storage.memory import MemoryStorage


def test_global_context_feature():
    with feature("global_test_feature"):
        pass


def test_resolve_pricing_edge_cases():
    assert _resolve_pricing("") == FALLBACK_PRICING
    assert _resolve_pricing(None) == FALLBACK_PRICING
    assert _resolve_pricing("GPT-4O")["input"] == 2.50
    assert _resolve_pricing("CLAUDE-3-5-SONNET")["input"] == 3.00


def test_auto_patch_openai():
    tracker = CostTracker(storage=MemoryStorage(), auto_patch=False)

    mock_resp = MagicMock()
    mock_resp.usage.prompt_tokens = 120
    mock_resp.usage.completion_tokens = 60

    import openai.resources.chat.completions as comp_module

    original_fn = comp_module.Completions.create
    try:
        comp_module.Completions.create = MagicMock(return_value=mock_resp)
        patch_openai(tracker)

        client = openai.OpenAI(api_key="test-key")
        with tracker.feature("test_openai_patch"):
            res = client.chat.completions.create(model="gpt-4o", messages=[])
            assert res == mock_resp

        events = tracker.storage.query(days=1)
        assert len(events) == 1
        assert events[0].feature == "test_openai_patch"
        assert events[0].input_tokens == 120
        assert events[0].output_tokens == 60
    finally:
        comp_module.Completions.create = original_fn


def test_auto_patch_anthropic():
    tracker = CostTracker(storage=MemoryStorage(), auto_patch=False)

    mock_resp = MagicMock()
    mock_resp.usage.input_tokens = 200
    mock_resp.usage.output_tokens = 80

    import anthropic.resources.messages as anth_mod

    original_fn = anth_mod.Messages.create
    try:
        anth_mod.Messages.create = MagicMock(return_value=mock_resp)
        patch_anthropic(tracker)

        client = anthropic.Anthropic(api_key="test-key")
        with tracker.feature("test_anthropic_patch"):
            res = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=100,
                messages=[{"role": "user", "content": "hi"}],
            )
            assert res == mock_resp

        events = tracker.storage.query(days=1)
        assert len(events) == 1
        assert events[0].feature == "test_anthropic_patch"
        assert events[0].input_tokens == 200
        assert events[0].output_tokens == 80
    finally:
        anth_mod.Messages.create = original_fn


def test_auto_patch_litellm():
    tracker = CostTracker(storage=MemoryStorage(), auto_patch=False)

    mock_resp = MagicMock()
    mock_resp.usage.prompt_tokens = 300
    mock_resp.usage.completion_tokens = 150

    original_fn = litellm.completion
    try:
        litellm.completion = MagicMock(return_value=mock_resp)
        patch_litellm(tracker)

        with tracker.feature("test_litellm_patch"):
            res = litellm.completion(model="gpt-4o", messages=[])
            assert res == mock_resp

        events = tracker.storage.query(days=1)
        assert len(events) == 1
        assert events[0].feature == "test_litellm_patch"
        assert events[0].input_tokens == 300
        assert events[0].output_tokens == 150
    finally:
        litellm.completion = original_fn


def test_set_budget_alert_default_print():
    storage = MemoryStorage()
    tracker = CostTracker(storage=storage, auto_patch=False)
    tracker.set_budget_alert("feature_warn", daily_limit_usd=0.001)

    with tracker.feature("feature_warn"):
        tracker.log_call("gpt-4o", 10_000, 5_000)

    from llmtrack.report.alerts import AlertManager

    triggered = AlertManager.check_all()
    assert len(triggered) == 1
    assert triggered[0]["feature"] == "feature_warn"
