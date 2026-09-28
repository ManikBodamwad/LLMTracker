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


def test_sqlite_migrates_old_schema(tmp_path):
    import sqlite3

    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE call_events (
            id TEXT PRIMARY KEY, feature TEXT NOT NULL, model TEXT NOT NULL,
            provider TEXT NOT NULL, input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL, total_tokens INTEGER NOT NULL,
            cost_usd REAL NOT NULL, latency_ms REAL NOT NULL,
            timestamp TEXT NOT NULL, metadata TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT INTO call_events VALUES ('old','f','gpt-4o','openai',1,1,2,0.5,1.0,?,'{}')",
        (datetime.now(timezone.utc).isoformat(),),
    )
    conn.commit()
    conn.close()

    storage = SQLiteStorage(db_path=db)
    (old,) = storage.query(days=1)
    assert old.id == "old"
    assert old.cached_input_tokens == 0
    assert old.estimated_pricing is False

    storage.save(_create_sample_event())
    assert len(storage.query(days=1)) == 2


def test_sqlite_normalizes_naive_and_offset_timestamps(tmp_path):
    storage = SQLiteStorage(db_path=tmp_path / "tz.db")
    naive = _create_sample_event()
    naive.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)  # naive = UTC
    offset = _create_sample_event()
    offset.timestamp = datetime.now(timezone(timedelta(hours=9)))
    old = _create_sample_event(days_ago=3)
    for event in (naive, offset, old):
        storage.save(event)

    assert {e.id for e in storage.query(days=1)} == {naive.id, offset.id}


@pytest.mark.parametrize("storage_cls", [MemoryStorage, SQLiteStorage])
def test_feature_cost(storage_cls, tmp_path):
    storage = (
        SQLiteStorage(db_path=tmp_path / "c.db")
        if storage_cls is SQLiteStorage
        else MemoryStorage()
    )
    storage.save(_create_sample_event("a", cost=0.25))
    storage.save(_create_sample_event("a", cost=0.50))
    storage.save(_create_sample_event("b", cost=9.0))
    storage.save(_create_sample_event("a", days_ago=3, cost=100.0))

    assert storage.feature_cost("a", days=1) == pytest.approx(0.75)
    assert storage.feature_cost("missing", days=1) == 0.0
