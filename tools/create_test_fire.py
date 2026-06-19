#!/usr/bin/env python3
"""
Create a test fire GeoJSON for Sentinela Verde.

Usage:
  python tools/create_test_fire.py [lat] [lon]

Drops a fake fire at the given coordinates (defaults to Serra do Cipó, MG).
On the next map refresh the server picks it up, displays it with source
"Teste", and deletes the file. It vanishes on the following refresh.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_LAT = -19.38
DEFAULT_LON = -43.63  # Serra do Cipó, MG

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "test_fire.geojson"


def main() -> None:
    lat = float(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LAT
    lon = float(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_LON

    now = datetime.now(UTC)

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "satellite": "Teste",
                    "acq_date": now.strftime("%Y-%m-%d"),
                    "acq_time": now.strftime("%H%M"),
                    "confidence": "h",
                    "frp": 75.0,
                    "brightness": None,
                    "scan": None,
                    "track": None,
                    "daynight": "D",
                },
            }
        ],
    }

    OUTPUT_PATH.write_text(json.dumps(geojson, indent=2), encoding="utf-8")
    print(f"Test fire written to: {OUTPUT_PATH}")
    print(f"  Location : {lat:.4f}, {lon:.4f}")
    print(f"  Aquisição: {now.strftime('%Y-%m-%d %H%M')} UTC")
    print("  Aparecerá no próximo refresh e sumirá no seguinte.")


if __name__ == "__main__":
    main()
