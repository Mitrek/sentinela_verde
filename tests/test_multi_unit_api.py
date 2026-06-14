from __future__ import annotations

import json

import anyio

import main


def test_api_fires_filters_multiple_units(monkeypatch):
    events = [{"id": 1}]
    filtered_events = [{"id": 2}]

    monkeypatch.setattr(main, "get_recent_events", lambda db_path, hours=48: events)
    monkeypatch.setattr(main, "get_operational_unit", lambda unit_id: {"id": unit_id})
    monkeypatch.setattr(
        main,
        "filter_events_by_operational_units",
        lambda source_events, unit_ids: filtered_events if unit_ids == ["unit-1", "unit-2"] else [],
    )

    response = anyio.run(main.api_fires, 48, None, ["unit-1", "unit-2"])

    assert json.loads(response.body) == filtered_events


def test_api_geojson_units_merges_multiple_units(monkeypatch):
    monkeypatch.setattr(main, "get_operational_unit", lambda unit_id: {"id": unit_id})
    monkeypatch.setattr(
        main,
        "get_operational_units_features",
        lambda unit_ids: [{"type": "Feature", "properties": {"id": "|".join(unit_ids)}}],
    )

    response = anyio.run(main.api_geojson_units, None, ["unit-1", "unit-2"])

    assert json.loads(response.body) == {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"id": "unit-1|unit-2"}}],
    }
