import concurrent.futures

import pytest

from llmtrack import CallEvent, CostTracker
from llmtrack.storage.memory import MemoryStorage
from llmtrack.tracker import _infer_provider


def test_log_call_creates_call_event(tracker):
    event = tracker.log_call(
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        feature="summarization",
        latency_ms=150.5,
        metadata={"user_id": "u1"},
    )
    assert isinstance(event, CallEvent)
    assert event.feature == "summarization"
    assert event.model == "gpt-4o"
    assert event.provider == "openai"
    assert event.input_tokens == 1000
    assert event.output_tokens == 500
    assert event.total_tokens == 1500
    assert event.latency_ms == 150.5
    assert event.metadata == {"user_id": "u1"}
    assert event.cost_usd > 0


def test_feature_context_manager(tracker):
    with tracker.feature("search_ranking"):
        event = tracker.log_call(
            model="gpt-4o-mini", input_tokens=100, output_tokens=50
        )
        assert event.feature == "search_ranking"


def test_nested_feature_context_manager(tracker):
    with tracker.feature("outer_feature"):
        e1 = tracker.log_call(model="gpt-4o", input_tokens=100, output_tokens=50)
        assert e1.feature == "outer_feature"

        with tracker.feature("inner_feature"):
            e2 = tracker.log_call(model="gpt-4o", input_tokens=100, output_tokens=50)
            assert e2.feature == "inner_feature"

        e3 = tracker.log_call(model="gpt-4o", input_tokens=100, output_tokens=50)
        assert e3.feature == "outer_feature"

    e4 = tracker.log_call(model="gpt-4o", input_tokens=100, output_tokens=50)
    assert e4.feature == "untagged"


def test_untagged_calls(tracker):
    event = tracker.log_call(
        model="claude-sonnet-4-5", input_tokens=200, output_tokens=100
    )
    assert event.feature == "untagged"
    assert event.provider == "anthropic"


def test_summary_totals_and_breakdown(tracker_with_data):
    summary = tracker_with_data.summary(days=7)
    assert summary["total_calls"] == 4
    assert summary["total_cost_usd"] > 0
    assert "feature_a" in summary["features"]
    assert "feature_b" in summary["features"]
    assert "feature_c" in summary["features"]
    assert summary["features"]["feature_a"]["calls"] == 2
    assert summary["features"]["feature_b"]["calls"] == 1
    assert summary["features"]["feature_c"]["calls"] == 1
    assert summary["period_days"] == 7


def test_report_terminal_and_html(tracker_with_data, tmp_path):
    # Should not raise on empty or populated data
    empty_tracker = CostTracker(storage=MemoryStorage(), auto_patch=False)
    empty_tracker.report(output="terminal")

    tracker_with_data.report(output="terminal")

    html_path = tmp_path / "test_report.html"
    tracker_with_data.report(output="html", filepath=str(html_path))
    assert html_path.exists()
    assert "llmtrack Cost Report" in html_path.read_text()


def test_report_invalid_format(tracker):
    with pytest.raises(ValueError, match="Unknown output format"):
        tracker.report(output="pdf")


def test_infer_provider():
    assert _infer_provider("gpt-4o") == "openai"
    assert _infer_provider("o1-mini") == "openai"
    assert _infer_provider("claude-sonnet-4-5") == "anthropic"
    assert _infer_provider("gemini-1.5-pro") == "google"
    assert _infer_provider("grok-2") == "xai"
    assert _infer_provider("deepseek-r1") == "deepseek"
    assert _infer_provider("mistral-large") == "mistral"
    assert _infer_provider("llama-3.3-70b") == "meta"
    assert _infer_provider("qwen-2.5-72b") == "alibaba"
    assert _infer_provider("command-r-plus") == "cohere"
    assert _infer_provider("custom-finetuned-v1") == "other"


def test_thread_safety_context(tracker):
    def worker(feature_name):
        with tracker.feature(feature_name):
            ev = tracker.log_call(model="gpt-4o", input_tokens=10, output_tokens=10)
            return ev.feature

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, f"thread_{i}") for i in range(10)]
        results = [f.result() for f in futures]

    assert results == [f"thread_{i}" for i in range(10)]


async def test_feature_isolated_between_asyncio_tasks(tracker):
    import asyncio

    async def worker(name):
        with tracker.feature(name):
            await asyncio.sleep(0.01)  # let the other tasks interleave
            return tracker.log_call("gpt-4o", 10, 10).feature

    results = await asyncio.gather(*(worker(f"task_{i}") for i in range(10)))
    assert results == [f"task_{i}" for i in range(10)]
    assert tracker.log_call("gpt-4o", 10, 10).feature == "untagged"


def test_global_feature_visible_to_any_tracker(tracker):
    from llmtrack import feature

    with feature("shared_tag"):
        assert tracker.log_call("gpt-4o", 1, 1).feature == "shared_tag"


def test_cached_tokens_reduce_cost(tracker):
    full = tracker.log_call("claude-sonnet-4-5", 1_000_000, 0)
    cached = tracker.log_call(
        "claude-sonnet-4-5", 1_000_000, 0, cached_input_tokens=1_000_000
    )
    assert full.cost_usd == pytest.approx(3.0)
    assert cached.cost_usd == pytest.approx(0.30)
    assert cached.cached_input_tokens == 1_000_000


def test_unknown_model_flagged_and_warned_once(tracker):
    import warnings

    from llmtrack import tracker as tracker_module

    tracker_module._WARNED_MODELS.discard("totally-new-model")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        first = tracker.log_call("totally-new-model", 100, 100)
        tracker.log_call("totally-new-model", 100, 100)
    assert first.estimated_pricing is True
    assert len([w for w in caught if "totally-new-model" in str(w.message)]) == 1
    assert tracker.summary()["estimated_calls"] == 2

    assert tracker.log_call("gpt-4o", 100, 100).estimated_pricing is False


def test_infer_provider_handles_prefixes_and_o_series():
    assert _infer_provider("openai/gpt-4o") == "openai"
    assert _infer_provider("azure/my-deployment") == "openai"
    assert _infer_provider("bedrock/anthropic.claude-3-haiku") == "anthropic"
    assert _infer_provider("o3-mini") == "openai"
    assert _infer_provider("foo1-bar") == "other"
