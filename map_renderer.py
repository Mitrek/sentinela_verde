from __future__ import annotations

import json
from pathlib import Path

import folium
from shapely.geometry import Point, Polygon

from areas import (
    GEOJSON_PATH,
    _normalize_name,
    filter_events_by_area,
    get_area_bounds,
    get_area_by_id,
)
from conservation_units import (
    filter_events_by_uc,
    get_uc_bounds,
    get_uc_feature,
)


MG_BOUNDARY = Polygon([
    (-44.0, -14.2), (-42.5, -14.5), (-41.0, -14.8), (-39.9, -15.8),
    (-40.2, -17.0), (-39.9, -18.5), (-41.0, -20.0), (-41.8, -21.2),
    (-43.0, -22.4), (-44.9, -22.9), (-46.5, -22.5), (-48.0, -21.5),
    (-50.0, -21.0), (-51.0, -19.5), (-51.0, -18.0), (-50.5, -16.5),
    (-49.0, -15.5), (-47.5, -14.5), (-46.0, -14.0), (-44.0, -14.2)
])

DEFAULT_CENTER = (-18.5, -44.5)
DEFAULT_ZOOM = 4


def _inside_mg(lat: float, lon: float) -> bool:
    return MG_BOUNDARY.contains(Point(lon, lat))


def _map_center(events: list[dict]) -> tuple[float, float]:
    if not events:
        return DEFAULT_CENTER

    latitudes = [float(event["latitude"]) for event in events]
    longitudes = [float(event["longitude"]) for event in events]
    return (sum(latitudes) / len(latitudes), sum(longitudes) / len(longitudes))


def _marker_color(frp: float | None) -> str:
    if frp is not None and frp > 100:
        return "red"
    if frp is not None and frp > 30:
        return "orange"
    return "yellow"


def _popup_html(event: dict) -> str:
    frp = event.get("frp")
    frp_display = f"{frp} MW" if frp is not None else "N/A"
    return (
        f"Date: {event.get('acq_date', 'N/A')}<br>"
        f"Time: {event.get('acq_time', 'N/A')}<br>"
        f"FRP: {frp_display}<br>"
        f"Satellite: {event.get('satellite', 'N/A')}<br>"
        f"Confidence: {event.get('confidence', 'N/A')}"
    )


def _render_base_map(events: list[dict]) -> folium.Map:
    center = _map_center(events)
    filtered_events = [event for event in events if _inside_mg(event["latitude"], event["longitude"])]
    zoom_start = DEFAULT_ZOOM if not filtered_events else 6
    fire_map = folium.Map(location=center, zoom_start=zoom_start)

    for event in filtered_events:
        color = _marker_color(event.get("frp"))
        folium.CircleMarker(
            location=[event["latitude"], event["longitude"]],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(_popup_html(event), max_width=300),
        ).add_to(fire_map)

    return fire_map


def _load_area_geojson_features(area_id: str) -> list[dict]:
    area = get_area_by_id(area_id)
    if area is None:
        return []

    municipios = {_normalize_name(name) for name in area.get("municipios", [])}
    with GEOJSON_PATH.open(encoding="utf-8") as geojson_file:
        geojson = json.load(geojson_file)

    features = []
    for feature in geojson.get("features", []):
        properties = feature.get("properties") or {}
        municipality_name = _normalize_name(properties.get("NM_MUN"))
        if municipality_name in municipios:
            features.append(feature)
    return features


def _render_filtered_map(
    events: list[dict],
    bounds: tuple[float, float, float, float],
    outline_features: list[dict],
    outline_color: str,
) -> str:
    min_lat, min_lon, max_lat, max_lon = bounds
    if events:
        center = _map_center(events)
    else:
        center = ((min_lat + max_lat) / 2, (min_lon + max_lon) / 2)

    fire_map = folium.Map(location=center, zoom_start=7)
    fire_map.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

    if outline_features:
        folium.GeoJson(
            {"type": "FeatureCollection", "features": outline_features},
            style_function=lambda _: {
                "color": outline_color,
                "weight": 2.5,
                "fill": True,
                "fillColor": outline_color,
                "fillOpacity": 0.15,
            },
        ).add_to(fire_map)

    for event in events:
        color = _marker_color(event.get("frp"))
        folium.CircleMarker(
            location=[event["latitude"], event["longitude"]],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(_popup_html(event), max_width=300),
        ).add_to(fire_map)

    return fire_map.get_root().render()


def render_map_html(
    events: list[dict],
    area_id: str | None = None,
    uc_id: str | None = None,
) -> str:
    """
    Like render_map, but returns the HTML string instead of saving to a file.
    Accepts an optional area_id to filter and zoom.

    If area_id is provided and valid:
      1. Import areas module and call filter_events_by_area(events, area_id)
      2. Get bounds via get_area_bounds(area_id); if available, fit the map to those bounds
         using folium.Map(location=center_of_bounds, zoom_start=7)
      3. Draw municipality outlines for the selected COB using folium.GeoJson
      4. Compute center from filtered events; if no events, use center of bounds

    If area_id is None or not found:
      - Behave exactly like render_map but return HTML string

    Fire markers use the same color logic and popup as render_map.
    Return fire_map.get_root().render() as a string.
    """
    try:
        if uc_id is not None and get_uc_feature(uc_id) is not None:
            filtered_events = filter_events_by_uc(events, uc_id)
            uc_bounds = get_uc_bounds(uc_id)
            uc_feature = get_uc_feature(uc_id)

            if uc_bounds is None or uc_feature is None:
                return _render_base_map(filtered_events).get_root().render()

            return _render_filtered_map(
                filtered_events,
                uc_bounds,
                [uc_feature],
                "#27ae60",
            )

        if area_id is None or get_area_by_id(area_id) is None:
            return _render_base_map(events).get_root().render()

        filtered_events = filter_events_by_area(events, area_id)
        area_bounds = get_area_bounds(area_id)

        if area_bounds is None:
            return _render_base_map(filtered_events).get_root().render()

        outline_features = _load_area_geojson_features(area_id)
        return _render_filtered_map(
            filtered_events,
            area_bounds,
            outline_features,
            "#e67e22",
        )
    except Exception as exc:
        print(f"Failed to render map HTML for area {area_id} or UC {uc_id}: {exc}")
        return _render_base_map(events).get_root().render()


def render_map(events: list[dict], output_path: str) -> None:
    """
    Render a Folium map.

    Center: centroid of all event lat/lons.
    Fallback if no events: center=(-15.0, -55.0), zoom=4.

    Each event → folium.CircleMarker:
      radius=5, fill=True, fill_opacity=0.7
      color + fill_color:
        frp > 100  → "red"
        frp > 30   → "orange"
        else       → "yellow"
      popup HTML: acq_date, acq_time, frp MW, satellite, confidence

    Save as HTML to output_path.
    """
    fire_map = _render_base_map(events)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fire_map.save(str(output_file))
