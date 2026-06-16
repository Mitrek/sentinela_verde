from __future__ import annotations

import json
from pathlib import Path

from scripts.build_simplified_municipalities import build_simplified_geojson


def test_build_simplified_geojson_keeps_identity_and_decoded_name(tmp_path):
    source_path = tmp_path / "municipalities.geojson"
    source_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [0, 0],
                                    [0.001, 0],
                                    [0.002, 0],
                                    [1, 0],
                                    [1, 1],
                                    [0, 1],
                                    [0, 0],
                                ]
                            ],
                        },
                        "properties": {
                            "CD_MUN": "3100000",
                            "NM_MUN": "BarÃ£o de Cocais",
                            "AREA_KM2": 340.0,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    output = build_simplified_geojson(source_path, tolerance=0.01)

    assert output["type"] == "FeatureCollection"
    assert len(output["features"]) == 1
    properties = output["features"][0]["properties"]
    assert properties == {
        "CD_MUN": "3100000",
        "NM_MUN": "BarÃ£o de Cocais",
        "sv_nome": "Barão de Cocais",
    }


def test_generated_simplified_geojson_has_all_municipalities():
    path = Path("sentinela_verde/web/static/geojson/mg_municipios_simplified.geojson")
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 853
    assert all("sv_nome" in feature["properties"] for feature in data["features"])


def test_frontend_declares_context_layer_and_loading_overlay():
    app_js = Path("sentinela_verde/web/static/js/app.js").read_text(encoding="utf-8")
    index_html = Path("sentinela_verde/web/templates/index.html").read_text(encoding="utf-8")
    style_css = Path("sentinela_verde/web/static/css/style.css").read_text(encoding="utf-8")

    assert "mg_municipios_simplified.geojson" in app_js
    assert "municipalityContextLayer" in app_js
    assert "waitForTileLayerReady" in app_js
    assert "await waitForTileLayerReady(tileLayers.dark)" in app_js
    assert "beginLoading" in app_js
    assert "loadingCount" in app_js
    assert "selectedUnitIds" in app_js
    assert "unitTreeSelectAll" in app_js
    assert "compactUnitName" in app_js
    assert "applyFiltersBtn" in app_js
    assert "Aplicar filtros" in index_html
    assert '"COB"' in app_js
    assert '"BBM"' in app_js
    assert "unit-tree-list" in index_html
    assert "Unidade BM" in index_html
    assert "unit-tree-checkbox" in style_css
    assert "background: transparent;" in style_css
    assert 'id="map-loading"' in index_html
