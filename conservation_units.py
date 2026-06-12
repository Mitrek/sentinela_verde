from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Point, shape


UCS_GEOJSON_PATH = Path(__file__).parent / "shapefiles" / "ucs.geojson"

_UCS_GEOJSON_CACHE: dict | None = None
_UC_GEOMETRY_CACHE: dict[str, object | None] = {}


def _load_ucs_geojson() -> dict:
    global _UCS_GEOJSON_CACHE

    if _UCS_GEOJSON_CACHE is None:
        with UCS_GEOJSON_PATH.open(encoding="utf-8") as geojson_file:
            _UCS_GEOJSON_CACHE = json.load(geojson_file)

    return _UCS_GEOJSON_CACHE


def load_ucs() -> list[dict]:
    """Return conservation unit summaries from the UC GeoJSON."""
    try:
        geojson = _load_ucs_geojson()
        ucs = []
        for feature in geojson.get("features", []):
            properties = feature.get("properties") or {}
            uc_id = feature.get("id")
            name = properties.get("nome_uc")
            if uc_id and name:
                ucs.append({"id": uc_id, "name": name})
        return sorted(ucs, key=lambda uc: uc["name"].casefold())
    except Exception as exc:
        print(f"Failed to load conservation units: {exc}")
        return []


def get_uc_feature(uc_id: str) -> dict | None:
    """Return the GeoJSON feature for a conservation unit id."""
    try:
        geojson = _load_ucs_geojson()
        for feature in geojson.get("features", []):
            if feature.get("id") == uc_id:
                return feature
    except Exception as exc:
        print(f"Failed to load conservation unit {uc_id}: {exc}")
    return None


def get_uc_geometry(uc_id: str) -> object | None:
    """Return a Shapely geometry for the selected conservation unit."""
    if uc_id in _UC_GEOMETRY_CACHE:
        return _UC_GEOMETRY_CACHE[uc_id]

    try:
        feature = get_uc_feature(uc_id)
        if feature is None:
            _UC_GEOMETRY_CACHE[uc_id] = None
            return None

        geometry = shape(feature["geometry"])
        _UC_GEOMETRY_CACHE[uc_id] = geometry
        return geometry
    except Exception as exc:
        print(f"Failed to build conservation unit geometry for {uc_id}: {exc}")
        _UC_GEOMETRY_CACHE[uc_id] = None
        return None


def filter_events_by_uc(events: list[dict], uc_id: str) -> list[dict]:
    """Return events whose coordinates fall within the selected conservation unit."""
    try:
        geometry = get_uc_geometry(uc_id)
        if geometry is None:
            return events

        filtered_events = []
        for event in events:
            point = Point(float(event["longitude"]), float(event["latitude"]))
            if geometry.covers(point):
                filtered_events.append(event)
        return filtered_events
    except Exception as exc:
        print(f"Failed to filter events for conservation unit {uc_id}: {exc}")
        return events


def get_uc_bounds(uc_id: str) -> tuple[float, float, float, float] | None:
    """Return (min_lat, min_lon, max_lat, max_lon) bounds for a conservation unit."""
    try:
        geometry = get_uc_geometry(uc_id)
        if geometry is None:
            return None

        min_lon, min_lat, max_lon, max_lat = geometry.bounds
        return (min_lat, min_lon, max_lat, max_lon)
    except Exception as exc:
        print(f"Failed to get conservation unit bounds for {uc_id}: {exc}")
        return None
