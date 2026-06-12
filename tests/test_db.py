from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from db import get_all_events, get_recent_events, init_db, insert_fire_events


def sample_event() -> dict:
    return {
        "latitude": -10.123,
        "longitude": -55.456,
        "brightness": 320.5,
        "scan": 0.39,
        "track": 0.36,
        "acq_date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "acq_time": "1420",
        "satellite": "N",
        "confidence": "nominal",
        "frp": 45.2,
        "daynight": "D",
    }


def test_init_db_creates_fire_events_table(tmp_path):
    db_path = tmp_path / "fires.db"

    init_db(str(db_path))

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'fire_events'"
        ).fetchone()

    assert row is not None


def test_insert_fire_events_returns_inserted_count(tmp_path):
    db_path = tmp_path / "fires.db"
    init_db(str(db_path))

    inserted = insert_fire_events(str(db_path), [sample_event()])

    assert inserted == 1
    stored_events = get_all_events(str(db_path))
    assert len(stored_events) == 1
    assert stored_events[0]["latitude"] == sample_event()["latitude"]


def test_duplicate_insert_is_ignored(tmp_path):
    db_path = tmp_path / "fires.db"
    init_db(str(db_path))
    event = sample_event()

    first_insert = insert_fire_events(str(db_path), [event])
    second_insert = insert_fire_events(str(db_path), [event])

    assert first_insert == 1
    assert second_insert == 0
    assert len(get_all_events(str(db_path))) == 1


def test_get_recent_events_returns_inserted_event_within_window(tmp_path):
    db_path = tmp_path / "fires.db"
    init_db(str(db_path))
    insert_fire_events(str(db_path), [sample_event()])

    recent_events = get_recent_events(str(db_path), hours=48)

    assert len(recent_events) == 1
    assert recent_events[0]["satellite"] == "N"


def test_get_recent_events_excludes_old_rows(tmp_path):
    db_path = tmp_path / "fires.db"
    init_db(str(db_path))
    insert_fire_events(str(db_path), [sample_event()])
    old_date = (datetime.now(UTC) - timedelta(hours=72)).strftime("%Y-%m-%d")

    with sqlite3.connect(db_path) as connection:
        connection.execute("UPDATE fire_events SET acq_date = ?", (old_date,))
        connection.commit()

    assert get_recent_events(str(db_path), hours=48) == []
