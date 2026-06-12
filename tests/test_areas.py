from __future__ import annotations

from shapely.geometry import Polygon

import areas


def test_get_mg_boundary_feature_returns_state_outline(monkeypatch):
    geometry = Polygon([(-45, -20), (-43, -20), (-43, -18), (-45, -18), (-45, -20)])
    monkeypatch.setattr(areas, "get_all_mg_geometry", lambda: geometry)

    feature = areas.get_mg_boundary_feature()

    assert feature is not None
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["properties"] == {"codarea": "31", "name": "Minas Gerais"}
