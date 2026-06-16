from __future__ import annotations

import json

import anyio

from sentinela_verde import main


def test_api_uc_fire_alerts_filters_current_unit(monkeypatch):
    events = [{"id": 1, "acq_date": "2026-06-12", "acq_time": "1300"}]
    filtered_events = [{"id": 1, "acq_date": "2026-06-12", "acq_time": "1300"}]
    alerts = [{"alert_key": "uc-1|N|2026-06-12T1300", "event_count": 1}]

    monkeypatch.setattr(main, "get_recent_events", lambda db_path, hours=48: events)
    monkeypatch.setattr(main, "get_operational_unit", lambda unit_id: {"id": unit_id})
    monkeypatch.setattr(
        main,
        "filter_events_by_operational_unit",
        lambda source_events, unit_id: filtered_events,
    )
    monkeypatch.setattr(
        main,
        "get_uc_fire_alert_groups",
        lambda source_events, after: alerts if source_events == filtered_events else [],
    )

    response = anyio.run(main.api_uc_fire_alerts, "2026-06-12T1200", "unit-1", None)

    assert json.loads(response.body) == alerts


def test_api_uc_fire_alerts_returns_empty_for_invalid_cursor():
    response = anyio.run(main.api_uc_fire_alerts, "invalid", None, None)

    assert json.loads(response.body) == []


def test_api_uc_fire_alerts_filters_multiple_units(monkeypatch):
    events = [{"id": 1, "acq_date": "2026-06-12", "acq_time": "1300"}]
    filtered_events = [{"id": 2, "acq_date": "2026-06-12", "acq_time": "1315"}]
    alerts = [{"alert_key": "uc-2|N|2026-06-12T1315", "event_count": 1}]

    monkeypatch.setattr(main, "get_recent_events", lambda db_path, hours=48: events)
    monkeypatch.setattr(main, "get_operational_unit", lambda unit_id: {"id": unit_id})
    monkeypatch.setattr(
        main,
        "filter_events_by_operational_units",
        lambda source_events, unit_ids: filtered_events if unit_ids == ["unit-1", "unit-2"] else [],
    )
    monkeypatch.setattr(
        main,
        "get_uc_fire_alert_groups",
        lambda source_events, after: alerts if source_events == filtered_events else [],
    )

    response = anyio.run(main.api_uc_fire_alerts, "2026-06-12T1200", None, ["unit-1", "unit-2"])

    assert json.loads(response.body) == alerts
