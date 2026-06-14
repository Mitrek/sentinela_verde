from __future__ import annotations

from shapely.geometry import Polygon

import areas
import operational_units


def test_get_mg_boundary_feature_returns_state_outline(monkeypatch):
    geometry = Polygon([(-45, -20), (-43, -20), (-43, -18), (-45, -18), (-45, -20)])
    monkeypatch.setattr(areas, "get_all_mg_geometry", lambda: geometry)

    feature = areas.get_mg_boundary_feature()

    assert feature is not None
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["properties"] == {"codarea": "31", "name": "Minas Gerais"}


def test_municipality_features_include_decoded_display_name(monkeypatch):
    raw_feature = {
        "type": "Feature",
        "geometry": None,
        "properties": {"NM_MUN": "BarÃ£o de Cocais"},
    }
    monkeypatch.setattr(areas, "_get_municipality_name_key", lambda: "NM_MUN")
    monkeypatch.setattr(
        areas,
        "_get_municipality_features_by_name",
        lambda: {"barao de cocais": raw_feature},
    )

    [feature] = areas.get_municipality_features(["Barão de Cocais"])

    assert feature["properties"]["NM_MUN"] == "BarÃ£o de Cocais"
    assert feature["properties"]["sv_nome"] == "Barão de Cocais"
    assert "sv_nome" not in raw_feature["properties"]


def test_all_mg_features_include_decoded_display_name(monkeypatch):
    raw_feature = {
        "type": "Feature",
        "geometry": None,
        "properties": {"NM_MUN": "AbaetÃ©"},
    }
    monkeypatch.setattr(areas, "_ALL_MG_FEATURES_CACHE", None)
    monkeypatch.setattr(areas, "_get_municipality_name_key", lambda: "NM_MUN")
    monkeypatch.setattr(areas, "_load_geojson", lambda: {"features": [raw_feature]})

    [feature] = areas.get_all_mg_features()

    assert feature["properties"]["NM_MUN"] == "AbaetÃ©"
    assert feature["properties"]["sv_nome"] == "Abaeté"


def test_operational_unit_features_include_decoded_display_name(monkeypatch):
    monkeypatch.setattr(
        operational_units,
        "get_operational_unit",
        lambda unit_id: {"id": unit_id, "municipios": ["São Gonçalo do Abaeté"]},
    )
    monkeypatch.setattr(
        operational_units,
        "get_municipality_features",
        lambda municipios: [
            {
                "type": "Feature",
                "geometry": None,
                "properties": {
                    "NM_MUN": "SÃ£o GonÃ§alo do AbaetÃ©",
                    "sv_nome": "São Gonçalo do Abaeté",
                },
            }
        ],
    )

    [feature] = operational_units.get_operational_unit_features("unit-1")

    assert feature["properties"]["NM_MUN"] == "SÃ£o GonÃ§alo do AbaetÃ©"
    assert feature["properties"]["sv_nome"] == "São Gonçalo do Abaeté"
