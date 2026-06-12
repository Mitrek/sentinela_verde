from __future__ import annotations

from shapely.geometry import Polygon

import conservation_units


def feature(uc_id: str, name: str, coordinates: list[tuple[float, float]]) -> dict:
    return {
        "type": "Feature",
        "id": uc_id,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[list(point) for point in coordinates]],
        },
        "properties": {"nome_uc": name},
    }


def reset_uc_caches() -> None:
    conservation_units._UC_FEATURE_GEOMETRIES_CACHE = None
    conservation_units._UCS_FOR_BOUNDARY_CACHE = {}


def test_get_ucs_for_boundary_returns_uc_inside_boundary(monkeypatch):
    reset_uc_caches()
    inside_uc = feature("uc-1", "Inside UC", [(1, 1), (2, 1), (2, 2), (1, 2), (1, 1)])
    outside_uc = feature("uc-2", "Outside UC", [(5, 5), (6, 5), (6, 6), (5, 6), (5, 5)])
    monkeypatch.setattr(
        conservation_units,
        "_load_ucs_geojson",
        lambda: {"type": "FeatureCollection", "features": [inside_uc, outside_uc]},
    )

    boundary = Polygon([(0, 0), (3, 0), (3, 3), (0, 3), (0, 0)])

    assert conservation_units.get_ucs_for_boundary("boundary-a", boundary) == [inside_uc]


def test_get_ucs_for_boundary_returns_crossing_uc_for_both_boundaries(monkeypatch):
    reset_uc_caches()
    crossing_uc = feature("uc-1", "Crossing UC", [(1, 1), (4, 1), (4, 2), (1, 2), (1, 1)])
    monkeypatch.setattr(
        conservation_units,
        "_load_ucs_geojson",
        lambda: {"type": "FeatureCollection", "features": [crossing_uc]},
    )

    left_boundary = Polygon([(0, 0), (2, 0), (2, 3), (0, 3), (0, 0)])
    right_boundary = Polygon([(3, 0), (5, 0), (5, 3), (3, 3), (3, 0)])

    assert conservation_units.get_ucs_for_boundary("boundary-left", left_boundary) == [crossing_uc]
    assert conservation_units.get_ucs_for_boundary("boundary-right", right_boundary) == [crossing_uc]


def test_get_ucs_for_boundary_excludes_outside_uc(monkeypatch):
    reset_uc_caches()
    outside_uc = feature("uc-1", "Outside UC", [(5, 5), (6, 5), (6, 6), (5, 6), (5, 5)])
    monkeypatch.setattr(
        conservation_units,
        "_load_ucs_geojson",
        lambda: {"type": "FeatureCollection", "features": [outside_uc]},
    )

    boundary = Polygon([(0, 0), (3, 0), (3, 3), (0, 3), (0, 0)])

    assert conservation_units.get_ucs_for_boundary("boundary-a", boundary) == []


def test_get_ucs_for_boundary_deduplicates_uc_ids(monkeypatch):
    reset_uc_caches()
    duplicate_a = feature("uc-1", "Duplicate UC", [(1, 1), (2, 1), (2, 2), (1, 2), (1, 1)])
    duplicate_b = feature("uc-1", "Duplicate UC", [(1.5, 1.5), (2.5, 1.5), (2.5, 2.5), (1.5, 2.5), (1.5, 1.5)])
    monkeypatch.setattr(
        conservation_units,
        "_load_ucs_geojson",
        lambda: {"type": "FeatureCollection", "features": [duplicate_a, duplicate_b]},
    )

    boundary = Polygon([(0, 0), (3, 0), (3, 3), (0, 3), (0, 0)])

    assert conservation_units.get_ucs_for_boundary("boundary-a", boundary) == [duplicate_a]


def test_get_uc_fire_alert_groups_filters_by_uc_and_after(monkeypatch):
    reset_uc_caches()
    inside_uc = feature("uc-1", "Inside UC", [(1, 1), (2, 1), (2, 2), (1, 2), (1, 1)])
    monkeypatch.setattr(
        conservation_units,
        "_load_ucs_geojson",
        lambda: {"type": "FeatureCollection", "features": [inside_uc]},
    )
    events = [
        {
            "id": 1,
            "latitude": 1.5,
            "longitude": 1.5,
            "acq_date": "2026-06-12",
            "acq_time": "1200",
            "satellite": "N",
            "frp": 45,
            "confidence": "n",
        },
        {
            "id": 2,
            "latitude": 5.5,
            "longitude": 5.5,
            "acq_date": "2026-06-12",
            "acq_time": "1300",
            "satellite": "N",
            "frp": 120,
            "confidence": "h",
        },
        {
            "id": 3,
            "latitude": 1.6,
            "longitude": 1.6,
            "acq_date": "2026-06-12",
            "acq_time": "1300",
            "satellite": "N",
            "frp": 120,
            "confidence": "h",
        },
    ]

    alerts = conservation_units.get_uc_fire_alert_groups(events, "2026-06-12T1200")

    assert len(alerts) == 1
    assert alerts[0]["alert_key"] == "uc-1|N|2026-06-12T1300"
    assert alerts[0]["uc_name"] == "Inside UC"
    assert alerts[0]["event_count"] == 1
    assert alerts[0]["max_frp"] == 120
    assert alerts[0]["max_intensity"] == "Alta"


def test_get_uc_fire_alert_groups_groups_multiple_events_same_pass(monkeypatch):
    reset_uc_caches()
    inside_uc = feature("uc-1", "Inside UC", [(1, 1), (3, 1), (3, 3), (1, 3), (1, 1)])
    monkeypatch.setattr(
        conservation_units,
        "_load_ucs_geojson",
        lambda: {"type": "FeatureCollection", "features": [inside_uc]},
    )
    events = [
        {
            "id": 1,
            "latitude": 1.5,
            "longitude": 1.5,
            "acq_date": "2026-06-12",
            "acq_time": "1300",
            "satellite": "N",
            "frp": 45,
            "confidence": "n",
        },
        {
            "id": 2,
            "latitude": 2.0,
            "longitude": 2.0,
            "acq_date": "2026-06-12",
            "acq_time": "1300",
            "satellite": "N",
            "frp": 80,
            "confidence": "n",
        },
    ]

    alerts = conservation_units.get_uc_fire_alert_groups(events, "2026-06-12T1200")

    assert len(alerts) == 1
    assert alerts[0]["event_count"] == 2
    assert alerts[0]["max_frp"] == 80
    assert alerts[0]["max_intensity"] == "Moderada"
