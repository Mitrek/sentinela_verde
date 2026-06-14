from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from shapely.geometry import mapping, shape


DEFAULT_TOLERANCE = 0.005


def decode_mojibake(value: str | None) -> str:
    if not value:
        return ""
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def simplify_feature(feature: dict[str, Any], tolerance: float) -> dict[str, Any]:
    properties = feature.get("properties") or {}
    geometry = shape(feature["geometry"]).simplify(tolerance, preserve_topology=True)

    return {
        "type": "Feature",
        "geometry": mapping(geometry),
        "properties": {
            "CD_MUN": properties.get("CD_MUN"),
            "NM_MUN": properties.get("NM_MUN"),
            "sv_nome": decode_mojibake(properties.get("NM_MUN")),
        },
    }


def build_simplified_geojson(source_path: Path, tolerance: float) -> dict[str, Any]:
    with source_path.open(encoding="utf-8") as source_file:
        source = json.load(source_file)

    return {
        "type": "FeatureCollection",
        "features": [
            simplify_feature(feature, tolerance)
            for feature in source.get("features", [])
            if feature.get("geometry")
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a lightweight MG municipality GeoJSON for browser context rendering."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("shapefiles/MG_Municipios_2025.geojson"),
        help="Full-resolution source municipality GeoJSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("static/geojson/mg_municipios_simplified.geojson"),
        help="Output path for simplified browser GeoJSON.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help="Shapely simplification tolerance in source CRS degrees.",
    )
    args = parser.parse_args()

    output = build_simplified_geojson(args.source, args.tolerance)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output_file:
        json.dump(output, output_file, ensure_ascii=False, separators=(",", ":"))
        output_file.write("\n")


if __name__ == "__main__":
    main()
