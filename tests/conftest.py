import pytest

from llmtrack import CostTracker
from llmtrack.report.alerts import AlertManager
from llmtrack.storage.memory import MemoryStorage


@pytest.fixture(autouse=True)
def cleanup_alerts():
    """Ensure alert state is clean between test runs."""
    AlertManager.clear()
    yield
    AlertManager.clear()


@pytest.fixture
def tracker():
    return CostTracker(storage=MemoryStorage(), auto_patch=False)


@pytest.fixture
def tracker_with_data(tracker):
    features = [
        ("feature_a", "gpt-4o", 500, 200),
        ("feature_a", "gpt-4o", 600, 250),
        ("feature_b", "gpt-4o-mini", 100, 50),
        ("feature_c", "claude-sonnet-4-5", 800, 300),
    ]
    for feature_name, model, inp, out in features:
        with tracker.feature(feature_name):
            tracker.log_call(model=model, input_tokens=inp, output_tokens=out)
    return tracker
