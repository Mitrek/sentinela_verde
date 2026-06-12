from __future__ import annotations

from shapely.geometry import Polygon

import map_renderer


def polygon_feature(feature_id: str, name: str, coordinates: list[tuple[float, float]]) -> dict:
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[list(point) for point in coordinates]],
        },
        "properties": {"NM_MUN": name, "nome_uc": name},
    }


def test_render_map_html_for_area_includes_cob_outline_and_linked_ucs(monkeypatch):
    event = {
        "latitude": -19.0,
        "longitude": -44.0,
        "acq_date": "2026-06-12",
        "acq_time": "1200",
        "frp": 45.0,
        "satellite": "N",
        "confidence": "nominal",
    }
    boundary_geometry = Polygon([(-45, -20), (-43, -20), (-43, -18), (-45, -18), (-45, -20)])
    cob_feature = polygon_feature("1COB", "Selected COB Outline", [(-45, -20), (-43, -20), (-43, -18), (-45, -18), (-45, -20)])
    uc_feature = polygon_feature("uc-1", "Linked UC Overlay", [(-44.5, -19.5), (-43.5, -19.5), (-43.5, -18.5), (-44.5, -18.5), (-44.5, -19.5)])

    monkeypatch.setattr(map_renderer, "get_area_by_id", lambda area_id: {"id": area_id})
    monkeypatch.setattr(map_renderer, "filter_events_by_area", lambda events, area_id: [event])
    monkeypatch.setattr(map_renderer, "get_area_bounds", lambda area_id: (-20, -45, -18, -43))
    monkeypatch.setattr(map_renderer, "get_area_geometry", lambda area_id: boundary_geometry)
    monkeypatch.setattr(map_renderer, "_load_area_geojson_features", lambda area_id: [cob_feature])
    monkeypatch.setattr(map_renderer, "get_ucs_for_boundary", lambda area_id, geometry: [uc_feature])

    html = map_renderer.render_map_html([event], area_id="1COB")

    assert "Selected COB Outline" in html
    assert "Linked UC Overlay" in html
    assert "Munic" in html
    assert "Unidade de Conserva" in html
    assert "sv_tipo" in html
    assert "sv_nome" in html
    assert "#cccccc" in html
    assert "#52b788" in html
    assert "fire-marker fire-marker--medium" in html
    assert "fire-marker-icon" not in html
    assert "\U0001F525" not in html
    assert "circleMarker" not in html


def test_render_map_html_for_operational_unit(monkeypatch):
    event = {
        "latitude": -19.0,
        "longitude": -44.0,
        "acq_date": "2026-06-12",
        "acq_time": "1200",
        "frp": 45.0,
        "satellite": "N",
        "confidence": "nominal",
    }
    boundary_geometry = Polygon([(-45, -20), (-43, -20), (-43, -18), (-45, -18), (-45, -20)])
    unit_feature = polygon_feature("unit-mun", "Município da Unidade", [(-45, -20), (-43, -20), (-43, -18), (-45, -18), (-45, -20)])
    uc_feature = polygon_feature("uc-1", "UC da Unidade", [(-44.5, -19.5), (-43.5, -19.5), (-43.5, -18.5), (-44.5, -18.5), (-44.5, -19.5)])

    monkeypatch.setattr(map_renderer, "get_operational_unit", lambda unit_id: {"id": unit_id})
    monkeypatch.setattr(map_renderer, "filter_events_by_operational_unit", lambda events, unit_id: [event])
    monkeypatch.setattr(map_renderer, "get_operational_unit_bounds", lambda unit_id: (-20, -45, -18, -43))
    monkeypatch.setattr(map_renderer, "get_operational_unit_geometry", lambda unit_id: boundary_geometry)
    monkeypatch.setattr(map_renderer, "get_operational_unit_features", lambda unit_id: [unit_feature])
    monkeypatch.setattr(map_renderer, "get_ucs_for_boundary", lambda unit_id, geometry: [uc_feature])

    html = map_renderer.render_map_html([event], unit_id="unit-1")

    assert "Munic" in html
    assert "da Unidade" in html
    assert "UC da Unidade" in html
    assert "#cccccc" in html
    assert "#52b788" in html
    assert "fire-marker fire-marker--medium" in html
    assert "fire-marker-icon" not in html
    assert "\U0001F525" not in html


def test_fire_popup_explains_detection_fields():
    html = map_renderer._popup_html(
        {
            "latitude": -19.0,
            "longitude": -44.0,
            "acq_date": "2026-06-12",
            "acq_time": "1200",
            "frp": 45.0,
            "satellite": "N",
            "confidence": "n",
        }
    )

    assert "Data da detecção" in html
    assert "Horário da detecção" in html
    assert "09:00 (horário de Brasília)" in html
    assert "Potência Radiativa do Fogo (FRP)" in html
    assert "FRP = Fire Radiative Power" in html
    assert "subtraia 3 horas" not in html
    assert "horário universal" not in html
    assert "\U0001F525" not in html
    assert "\U0001F4CD" not in html


def test_fire_marker_level_and_size_by_intensity():
    assert map_renderer._fire_marker_level(10) == "low"
    assert map_renderer._fire_marker_size("low") == 17
    assert map_renderer._fire_marker_level(45) == "medium"
    assert map_renderer._fire_marker_size("medium") == 22
    assert map_renderer._fire_marker_level(120) == "high"
    assert map_renderer._fire_marker_size("high") == 26
