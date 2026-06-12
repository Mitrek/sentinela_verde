from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta


CREATE_FIRE_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fire_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    brightness REAL,
    scan REAL,
    track REAL,
    acq_date TEXT,
    acq_time TEXT,
    satellite TEXT,
    confidence TEXT,
    frp REAL,
    daynight TEXT,
    fetched_at TEXT NOT NULL,
    UNIQUE(latitude, longitude, acq_date, acq_time, satellite)
);
"""

INSERT_FIRE_EVENT_SQL = """
INSERT OR IGNORE INTO fire_events (
    latitude,
    longitude,
    brightness,
    scan,
    track,
    acq_date,
    acq_time,
    satellite,
    confidence,
    frp,
    daynight,
    fetched_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

SELECT_COLUMNS = """
SELECT
    id,
    latitude,
    longitude,
    brightness,
    scan,
    track,
    acq_date,
    acq_time,
    satellite,
    confidence,
    frp,
    daynight,
    fetched_at
FROM fire_events
"""


def _get_connection(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _event_values(event: dict, fetched_at: str) -> tuple:
    return (
        event["latitude"],
        event["longitude"],
        event.get("brightness"),
        event.get("scan"),
        event.get("track"),
        event.get("acq_date"),
        event.get("acq_time"),
        event.get("satellite"),
        event.get("confidence"),
        event.get("frp"),
        event.get("daynight"),
        fetched_at,
    )


def init_db(db_path: str) -> None:
    """Create fire_events table if not exists."""
    with _get_connection(db_path) as connection:
        connection.execute(CREATE_FIRE_EVENTS_TABLE_SQL)
        connection.commit()


def insert_fire_events(db_path: str, events: list[dict]) -> int:
    """
    Insert list of fire event dicts.
    Use INSERT OR IGNORE to skip duplicates silently.
    Set fetched_at to current UTC ISO datetime on insert.
    Return count of newly inserted rows.
    """
    if not events:
        return 0

    fetched_at = datetime.now(UTC).isoformat()

    with _get_connection(db_path) as connection:
        cursor = connection.cursor()
        inserted_count = 0

        for event in events:
            cursor.execute(INSERT_FIRE_EVENT_SQL, _event_values(event, fetched_at))
            if cursor.rowcount > 0:
                inserted_count += 1

        connection.commit()
        return inserted_count


def get_recent_events(db_path: str, hours: int = 48) -> list[dict]:
    """Return events acquired within the last `hours` hours as list of dicts."""
    cutoff_date = (datetime.now(UTC) - timedelta(hours=hours)).strftime("%Y-%m-%d")

    with _get_connection(db_path) as connection:
        rows = connection.execute(
            f"""
            {SELECT_COLUMNS}
            WHERE acq_date >= ?
            ORDER BY acq_date DESC, acq_time DESC, id DESC
            """,
            (cutoff_date,),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def get_all_events(db_path: str) -> list[dict]:
    """Return all stored events as list of dicts."""
    with _get_connection(db_path) as connection:
        rows = connection.execute(
            f"""
            {SELECT_COLUMNS}
            ORDER BY acq_date DESC, acq_time DESC, id DESC
            """
        ).fetchall()

    return [_row_to_dict(row) for row in rows]
