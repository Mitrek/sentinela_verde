from __future__ import annotations

from fastapi.testclient import TestClient

import main


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

    client = TestClient(main.app)
    response = client.get("/api/alerts/uc-fires?unit=unit-1&after=2026-06-12T1200")

    assert response.status_code == 200
    assert response.json() == alerts


def test_api_uc_fire_alerts_returns_empty_for_invalid_cursor():
    client = TestClient(main.app)
    response = client.get("/api/alerts/uc-fires?after=invalid")

    assert response.status_code == 200
    assert response.json() == []
