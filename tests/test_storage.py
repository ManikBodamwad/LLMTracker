import uuid
from datetime import datetime, timedelta, timezone

import pytest

from llmtrack.storage.memory import MemoryStorage
from llmtrack.storage.sqlite import SQLiteStorage
from llmtrack.tracker import CallEvent


def _create_sample_event(feature="test_feature", days_ago=0, cost=0.01):
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return CallEvent(
        id=str(uuid.uuid4()),
        feature=feature,
        model="gpt-4o",
        provider="openai",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        cost_usd=cost,
        latency_ms=120.0,
        timestamp=ts,
        metadata={"test": True},
    )


@pytest.mark.parametrize("storage_cls", [MemoryStorage, SQLiteStorage])
def test_storage_crud(storage_cls, tmp_path):
    if storage_cls == SQLiteStorage:
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(db_path=db_path)
    else:
        storage = MemoryStorage()

    # Initial query on empty
    assert storage.query(days=7) == []

    # Save event
    e1 = _create_sample_event(days_ago=1)
    e2 = _create_sample_event(days_ago=10)  # older than 7 days
    storage.save(e1)
    storage.save(e2)

    # Query 7 days
    results_7d = storage.query(days=7)
    assert len(results_7d) == 1
    assert results_7d[0].id == e1.id
    assert results_7d[0].metadata == {"test": True}

    # Query 15 days
    results_15d = storage.query(days=15)
    assert len(results_15d) == 2

    # Clear
    storage.clear()
    assert storage.query(days=30) == []
