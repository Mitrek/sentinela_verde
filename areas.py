from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.ops import unary_union


AREAS_JSON_PATH = Path(__file__).parent / "articulation" / "areas.json"
GEOJSON_PATH = Path(__file__).parent / "shapefiles" / "MG_Municipios_2025.geojson"

_AREAS_CACHE: list[dict] | None = None
_AREA_GEOMETRY_CACHE: dict[str, object | None] = {}
_MUNICIPALITY_FEATURES_BY_NAME_CACHE: dict[str, dict] | None = None
_GEOJSON_CACHE: dict | None = None
_MUNICIPALITY_KEY_CACHE: str | None = None


def _normalize_name(value: str | None) -> str:
    if not value:
        return ""
    # GeoJSON was saved with mojibake (UTF-8 bytes decoded as Latin-1).
    # Re-encoding as Latin-1 and decoding as UTF-8 recovers the original chars.
    try:
        value = value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_accents.replace("'", "").strip().casefold()


def _decode_mojibake(value: str | None) -> str:
    if not value:
        return ""
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _load_geojson() -> dict:
    global _GEOJSON_CACHE

    if _GEOJSON_CACHE is None:
        with GEOJSON_PATH.open(encoding="utf-8") as geojson_file:
            _GEOJSON_CACHE = json.load(geojson_file)

    return _GEOJSON_CACHE


def _get_municipality_name_key() -> str | None:
    global _MUNICIPALITY_KEY_CACHE

    if _MUNICIPALITY_KEY_CACHE is not None:
        return _MUNICIPALITY_KEY_CACHE

    geojson = _load_geojson()
    features = geojson.get("features") or []
    if not features:
        print("GeoJSON does not contain features")
        return None

    properties = features[0].get("properties") or {}
    property_keys = list(properties.keys())
    print(f"GeoJSON municipality properties keys: {property_keys}")

    if "NM_MUN" in properties:
        _MUNICIPALITY_KEY_CACHE = "NM_MUN"
        return _MUNICIPALITY_KEY_CACHE

    for key in property_keys:
        normalized_key = key.casefold()
        if "mun" in normalized_key or "municip" in normalized_key or "name" in normalized_key:
            _MUNICIPALITY_KEY_CACHE = key
            return _MUNICIPALITY_KEY_CACHE

    print("Unable to determine municipality name property key")
    return None


def _get_area_municipios(area_id: str) -> set[str] | None:
    area = get_area_by_id(area_id)
    if area is None:
        return None
    return {_normalize_name(name) for name in area.get("municipios", [])}


def _get_municipality_features_by_name() -> dict[str, dict]:
    global _MUNICIPALITY_FEATURES_BY_NAME_CACHE

    if _MUNICIPALITY_FEATURES_BY_NAME_CACHE is not None:
        return _MUNICIPALITY_FEATURES_BY_NAME_CACHE

    municipality_key = _get_municipality_name_key()
    if municipality_key is None:
        _MUNICIPALITY_FEATURES_BY_NAME_CACHE = {}
        return _MUNICIPALITY_FEATURES_BY_NAME_CACHE

    features_by_name = {}
    for feature in _load_geojson().get("features", []):
        properties = feature.get("properties") or {}
        normalized_name = _normalize_name(properties.get(municipality_key))
        if normalized_name:
            features_by_name[normalized_name] = feature

    _MUNICIPALITY_FEATURES_BY_NAME_CACHE = features_by_name
    return features_by_name


def get_municipality_names() -> list[str]:
    """Return display names for all municipalities present in the MG GeoJSON."""
    municipality_key = _get_municipality_name_key()
    if municipality_key is None:
        return []

    names = []
    for feature in _load_geojson().get("features", []):
        properties = feature.get("properties") or {}
        name = properties.get(municipality_key)
        if name:
            names.append(_decode_mojibake(name))
    return names


def get_municipality_features(municipios: list[str] | set[str]) -> list[dict]:
    """Return GeoJSON municipality features matching the provided names."""
    features_by_name = _get_municipality_features_by_name()
    features = []
    seen_names = set()
    for municipio in municipios:
        normalized_name = _normalize_name(municipio)
        if normalized_name in seen_names:
            continue
        feature = features_by_name.get(normalized_name)
        if feature is not None:
            features.append(feature)
            seen_names.add(normalized_name)
    return features


def build_municipality_geometry(
    municipios: list[str] | set[str],
    cache_key: str | None = None,
) -> object | None:
    """Return a cached unary_union for a set of municipality names."""
    if cache_key and cache_key in _AREA_GEOMETRY_CACHE:
        return _AREA_GEOMETRY_CACHE[cache_key]

    try:
        geometries = [
            shape(feature["geometry"])
            for feature in get_municipality_features(municipios)
            if feature.get("geometry")
        ]

        if not geometries:
            if cache_key:
                _AREA_GEOMETRY_CACHE[cache_key] = None
            return None

        geometry = unary_union(geometries)
        if cache_key:
            _AREA_GEOMETRY_CACHE[cache_key] = geometry
        return geometry
    except Exception as exc:
        print(f"Failed to build municipality geometry {cache_key or ''}: {exc}")
        if cache_key:
            _AREA_GEOMETRY_CACHE[cache_key] = None
        return None


def load_areas() -> list[dict]:
    """
    Return the list of COB dicts from areas.json.
    Each dict has: id, name, region, hq, units, municipios.
    Cache the result in a module-level variable after first load.
    """
    global _AREAS_CACHE

    if _AREAS_CACHE is None:
        try:
            with AREAS_JSON_PATH.open(encoding="utf-8") as areas_file:
                data = json.load(areas_file)
            _AREAS_CACHE = data.get("cobs", [])
        except Exception as exc:
            print(f"Failed to load areas: {exc}")
            _AREAS_CACHE = []

    return _AREAS_CACHE


def get_area_by_id(area_id: str) -> dict | None:
    """Return the COB dict for the given id (e.g. '1COB'), or None if not found."""
    for area in load_areas():
        if area.get("id") == area_id:
            return area
    return None


def get_area_geometry(area_id: str) -> object | None:
    """
    Return a Shapely geometry (unary_union of municipality polygons) for the given COB.

    Steps:
    1. Load areas.json → find the COB with matching id → get its `municipios` list
    2. Load the GeoJSON file
    3. Inspect the municipality name property key (likely NM_MUN — verify at runtime)
    4. For each GeoJSON feature whose name is in the COB's `municipios` list,
       build a Shapely geometry via shape(feature["geometry"])
    5. Return unary_union of all matched geometries

    Cache geometries per area_id in a module-level dict after first computation.
    On any error: print the error and return None.
    """
    if area_id in _AREA_GEOMETRY_CACHE:
        return _AREA_GEOMETRY_CACHE[area_id]

    try:
        municipality_names = _get_area_municipios(area_id)
        if municipality_names is None:
            _AREA_GEOMETRY_CACHE[area_id] = None
            return None

        geometry = build_municipality_geometry(
            municipality_names,
            cache_key=area_id,
        )
        if geometry is None:
            print(f"No geometries matched area {area_id}")
            return None

        return geometry
    except Exception as exc:
        print(f"Failed to build geometry for area {area_id}: {exc}")
        _AREA_GEOMETRY_CACHE[area_id] = None
        return None


def filter_events_by_area(events: list[dict], area_id: str) -> list[dict]:
    """
    Return only the events whose (latitude, longitude) falls within
    the Shapely geometry of the given area_id.
    If geometry is None (load error), return all events unchanged.
    """
    try:
        geometry = get_area_geometry(area_id)
        if geometry is None:
            return events

        filtered_events = []
        for event in events:
            point = Point(float(event["longitude"]), float(event["latitude"]))
            if geometry.covers(point):
                filtered_events.append(event)
        return filtered_events
    except Exception as exc:
        print(f"Failed to filter events for area {area_id}: {exc}")
        return events


_ALL_MG_GEOMETRY_CACHE: object | None = None
_ALL_MG_FEATURES_CACHE: list[dict] | None = None


def get_all_mg_features() -> list[dict]:
    """Return all 853 municipality GeoJSON features for Minas Gerais."""
    global _ALL_MG_FEATURES_CACHE
    if _ALL_MG_FEATURES_CACHE is not None:
        return _ALL_MG_FEATURES_CACHE
    try:
        _ALL_MG_FEATURES_CACHE = _load_geojson().get("features", [])
        return _ALL_MG_FEATURES_CACHE
    except Exception as exc:
        print(f"Failed to load all MG features: {exc}")
        return []


def get_all_mg_geometry() -> object | None:
    """Return unary_union of all 853 MG municipality geometries (cached)."""
    global _ALL_MG_GEOMETRY_CACHE
    if _ALL_MG_GEOMETRY_CACHE is not None:
        return _ALL_MG_GEOMETRY_CACHE
    try:
        geometries = [
            shape(f["geometry"])
            for f in get_all_mg_features()
            if f.get("geometry")
        ]
        if not geometries:
            return None
        _ALL_MG_GEOMETRY_CACHE = unary_union(geometries)
        return _ALL_MG_GEOMETRY_CACHE
    except Exception as exc:
        print(f"Failed to build all-MG geometry: {exc}")
        return None


def filter_events_by_mg(events: list[dict]) -> list[dict]:
    """Return only events that fall within actual MG municipality boundaries."""
    try:
        geometry = get_all_mg_geometry()
        if geometry is None:
            return events
        return [
            e for e in events
            if geometry.covers(Point(float(e["longitude"]), float(e["latitude"])))
        ]
    except Exception as exc:
        print(f"Failed to filter events by MG boundary: {exc}")
        return events


def get_area_bounds(area_id: str) -> tuple[float, float, float, float] | None:
    """
    Return (min_lat, min_lon, max_lat, max_lon) bounding box of the area geometry.
    Returns None if geometry is unavailable.
    Used by map_renderer to fit the map to the selected area.
    """
    try:
        geometry = get_area_geometry(area_id)
        if geometry is None:
            return None

        min_lon, min_lat, max_lon, max_lat = geometry.bounds
        return (min_lat, min_lon, max_lat, max_lon)
    except Exception as exc:
        print(f"Failed to get bounds for area {area_id}: {exc}")
        return None
