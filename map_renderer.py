from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import folium
from shapely.geometry import Point

from areas import (
    GEOJSON_PATH,
    _normalize_name,
    filter_events_by_area,
    filter_events_by_mg,
    get_all_mg_features,
    get_area_bounds,
    get_area_by_id,
    get_area_geometry,
)
from conservation_units import (
    filter_events_by_uc,
    get_all_uc_features,
    get_ucs_for_boundary,
    get_uc_bounds,
    get_uc_feature,
)
from operational_units import (
    filter_events_by_operational_unit,
    get_operational_unit,
    get_operational_unit_bounds,
    get_operational_unit_features,
    get_operational_unit_geometry,
)


DEFAULT_CENTER = (-18.5, -44.5)
DEFAULT_ZOOM = 6
UC_OVERLAY_COLOR = "#27ae60"
MUNICIPALITY_COLOR = "#F48030"


def _decode_display_text(value: object) -> str:
    if value is None:
        return "Não informado"

    text = str(value)
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _features_with_tooltip_properties(
    features: list[dict],
    feature_type: str,
    name_property: str,
) -> list[dict]:
    tooltip_features = []
    for feature in features:
        tooltip_feature = deepcopy(feature)
        properties = tooltip_feature.setdefault("properties", {})
        properties["sv_tipo"] = feature_type
        properties["sv_nome"] = _decode_display_text(properties.get(name_property))
        tooltip_features.append(tooltip_feature)
    return tooltip_features


def _map_center(events: list[dict]) -> tuple[float, float]:
    if not events:
        return DEFAULT_CENTER

    latitudes = [float(event["latitude"]) for event in events]
    longitudes = [float(event["longitude"]) for event in events]
    return (sum(latitudes) / len(latitudes), sum(longitudes) / len(longitudes))


def _fire_marker_level(frp: float | None) -> str:
    if frp is not None and frp > 100:
        return "high"
    if frp is not None and frp > 30:
        return "medium"
    return "low"


def _fire_marker_size(level: str) -> int:
    return {
        "high": 22,
        "medium": 17,
        "low": 12,
    }.get(level, 12)


def _fire_marker_html(level: str) -> str:
    return f'<span class="fire-marker fire-marker--{level}"></span>'


def _add_fire_marker(fire_map: folium.Map, event: dict) -> None:
    level = _fire_marker_level(event.get("frp"))
    size = _fire_marker_size(level)
    folium.Marker(
        location=[event["latitude"], event["longitude"]],
        icon=folium.DivIcon(
            html=_fire_marker_html(level),
            icon_size=(size, size),
            icon_anchor=(size / 2, size / 2),
            popup_anchor=(0, -(size / 2)),
            class_name="fire-div-icon",
        ),
        popup=folium.Popup(_popup_html(event), max_width=420),
    ).add_to(fire_map)


_CONFIDENCE_LABELS = {
    # VIIRS categorical
    "l": "Baixa (~35%) — possível falso positivo",
    "n": "Nominal (~75%) — provável foco real",
    "h": "Alta (~95%) — foco confirmado",
    # MODIS numeric bands (stored as strings)
}

_SATELLITE_LABELS = {
    "Terra": "Terra (MODIS)",
    "Aqua":  "Aqua (MODIS)",
    "N": "NOAA-20 / VIIRS",
    "N-20": "NOAA-20 / VIIRS",
    "NOAA-20": "NOAA-20 / VIIRS",
    "S": "Suomi NPP / VIIRS",
    "NPP": "Suomi NPP / VIIRS",
}


def _format_confidence(raw: str | None) -> str:
    if raw is None:
        return "Não informado"
    key = str(raw).strip().lower()
    # VIIRS categorical
    label = _CONFIDENCE_LABELS.get(key)
    if label:
        return label
    # MODIS numeric (0–100)
    try:
        pct = int(float(raw))
        if pct >= 80:
            tier = "Alta"
        elif pct >= 50:
            tier = "Nominal"
        else:
            tier = "Baixa"
        return f"{tier} ({pct}%) — {'foco confirmado' if pct >= 80 else 'provável foco real' if pct >= 50 else 'possível falso positivo'}"
    except (ValueError, TypeError):
        return str(raw)


def _format_time(raw: str | None) -> str:
    if raw is None:
        return "Não informado"
    t = str(raw).zfill(4)
    return f"{t[:2]}h{t[2:]} UTC ({t[:2]}:{t[2:]} no horário universal)"


def _format_frp(frp: float | None) -> str:
    if frp is None:
        return "Não informado"
    if frp > 100:
        intensity = "Alta intensidade"
    elif frp > 30:
        intensity = "Intensidade moderada"
    else:
        intensity = "Baixa intensidade"
    return f"{frp} MW — {intensity}"


def _format_satellite(raw: str | None) -> str:
    if raw is None:
        return "Não informado"
    return _SATELLITE_LABELS.get(str(raw), str(raw))


def _popup_html(event: dict) -> str:
    frp      = event.get("frp")
    date     = event.get("acq_date", "Não informado")
    daynight = event.get("daynight", "")
    period   = " (diurno)" if daynight == "D" else " (noturno)" if daynight == "N" else ""

    rows = [
        ("Data da detecção", f"{date}{period} — dia em que o satélite identificou este foco"),
        ("Horário da detecção", f"{_format_time(event.get('acq_time'))}; em Brasília, subtraia 3 horas"),
        ("Potência Radiativa do Fogo (FRP)", _format_frp(frp) + " — estimativa da energia/calor emitido pelo fogo no momento da passagem do satélite"),
        ("Satélite/sensor", _format_satellite(event.get("satellite")) + " — plataforma que detectou o foco"),
        ("Confiança da detecção", _format_confidence(event.get("confidence"))),
        ("Coordenadas", f"{event.get('latitude', ''):.4f}, {event.get('longitude', ''):.4f}"),
    ]

    inner = "".join(
        f'<tr><td style="color:#666;padding:5px 10px 5px 0;vertical-align:top;'
        f'font-weight:700;min-width:150px">{label}</td>'
        f'<td style="padding:5px 0;font-size:12px;line-height:1.35">{value}</td></tr>'
        for label, value in rows
    )

    return (
        '<div style="font-family:system-ui,sans-serif;font-size:13px;min-width:330px;max-width:390px">'
        '<div style="font-weight:700;font-size:15px;margin-bottom:6px;padding-bottom:6px;'
        'border-bottom:2px solid #F48030">Foco de Incêndio</div>'
        '<div style="font-size:12px;color:#555;margin-bottom:8px;line-height:1.35">'
        'Registro de detecção por satélite da NASA FIRMS. Não é despacho operacional nem confirmação em campo.'
        '</div>'
        f'<table style="border-collapse:collapse;width:100%">{inner}</table>'
        '<div style="margin-top:8px;font-size:11px;color:#777;line-height:1.35">'
        'FRP = Fire Radiative Power, ou Potência Radiativa do Fogo. Valores maiores indicam maior energia emitida pelo foco.</div>'
        '</div>'
    )


def _render_base_map(events: list[dict]) -> folium.Map:
    filtered_events = filter_events_by_mg(events)
    fire_map = folium.Map(location=DEFAULT_CENTER, zoom_start=DEFAULT_ZOOM)

    # All 853 MG municipalities
    municipality_features = get_all_mg_features()
    if municipality_features:
        folium.GeoJson(
            {
                "type": "FeatureCollection",
                "features": _features_with_tooltip_properties(
                    municipality_features, "Município", "NM_MUN"
                ),
            },
            name="Municípios de MG",
            style_function=lambda _: {
                "color": MUNICIPALITY_COLOR,
                "weight": 0.8,
                "fill": True,
                "fillColor": MUNICIPALITY_COLOR,
                "fillOpacity": 0.05,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["sv_tipo", "sv_nome"],
                aliases=["Tipo:", "Nome:"],
                sticky=True,
            ),
        ).add_to(fire_map)

    # All UCs in MG
    uc_features = get_all_uc_features()
    if uc_features:
        folium.GeoJson(
            {
                "type": "FeatureCollection",
                "features": _features_with_tooltip_properties(
                    uc_features, "Unidade de Conservação", "nome_uc"
                ),
            },
            name="Unidades de Conservação",
            style_function=lambda _: {
                "color": UC_OVERLAY_COLOR,
                "weight": 1.5,
                "fill": True,
                "fillColor": UC_OVERLAY_COLOR,
                "fillOpacity": 0.2,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["sv_tipo", "sv_nome"],
                aliases=["Tipo:", "Nome:"],
                sticky=True,
            ),
        ).add_to(fire_map)

    for event in filtered_events:
        _add_fire_marker(fire_map, event)

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
    overlay_features: list[dict] | None = None,
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
            {
                "type": "FeatureCollection",
                "features": _features_with_tooltip_properties(
                    outline_features,
                    "Município",
                    "NM_MUN",
                ),
            },
            name="COB selecionado",
            style_function=lambda _: {
                "color": outline_color,
                "weight": 2.5,
                "fill": True,
                "fillColor": outline_color,
                "fillOpacity": 0.15,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["sv_tipo", "sv_nome"],
                aliases=["Tipo:", "Nome:"],
                sticky=True,
            ),
        ).add_to(fire_map)

    if overlay_features:
        folium.GeoJson(
            {
                "type": "FeatureCollection",
                "features": _features_with_tooltip_properties(
                    overlay_features,
                    "Unidade de Conservação",
                    "nome_uc",
                ),
            },
            name="Unidades de Conservação sobrepostas",
            style_function=lambda _: {
                "color": UC_OVERLAY_COLOR,
                "weight": 2,
                "fill": True,
                "fillColor": UC_OVERLAY_COLOR,
                "fillOpacity": 0.25,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["sv_tipo", "sv_nome"],
                aliases=["Tipo:", "Nome:"],
                sticky=True,
            ),
        ).add_to(fire_map)

    for event in events:
        _add_fire_marker(fire_map, event)

    return fire_map.get_root().render()


def render_map_html(
    events: list[dict],
    area_id: str | None = None,
    unit_id: str | None = None,
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

    Fire markers use circular DivIcon markers and the same popup as render_map.
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
                UC_OVERLAY_COLOR,
            )

        if unit_id is not None and get_operational_unit(unit_id) is not None:
            filtered_events = filter_events_by_operational_unit(events, unit_id)
            unit_bounds = get_operational_unit_bounds(unit_id)
            unit_geometry = get_operational_unit_geometry(unit_id)

            if unit_bounds is None:
                return _render_base_map(filtered_events).get_root().render()

            outline_features = get_operational_unit_features(unit_id)
            uc_features = get_ucs_for_boundary(unit_id, unit_geometry)
            return _render_filtered_map(
                filtered_events,
                unit_bounds,
                outline_features,
                MUNICIPALITY_COLOR,
                uc_features,
            )

        if area_id is None or get_area_by_id(area_id) is None:
            return _render_base_map(events).get_root().render()

        filtered_events = filter_events_by_area(events, area_id)
        area_bounds = get_area_bounds(area_id)
        area_geometry = get_area_geometry(area_id)

        if area_bounds is None:
            return _render_base_map(filtered_events).get_root().render()

        outline_features = _load_area_geojson_features(area_id)
        uc_features = get_ucs_for_boundary(area_id, area_geometry)
        return _render_filtered_map(
            filtered_events,
            area_bounds,
            outline_features,
            MUNICIPALITY_COLOR,
            uc_features,
        )
    except Exception as exc:
        print(f"Failed to render map HTML for area {area_id}, unit {unit_id}, or UC {uc_id}: {exc}")
        return _render_base_map(events).get_root().render()


def render_map(events: list[dict], output_path: str) -> None:
    """
    Render a Folium map.

    Center: centroid of all event lat/lons.
    Fallback if no events: center=(-15.0, -55.0), zoom=4.

    Each event → folium.Marker with a circular DivIcon:
      frp > 100  → high marker
      frp > 30   → medium marker
      else       → low marker
      popup HTML: acq_date, acq_time, frp MW, satellite, confidence

    Save as HTML to output_path.
    """
    fire_map = _render_base_map(events)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fire_map.save(str(output_file))
