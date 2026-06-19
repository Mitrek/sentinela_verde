from __future__ import annotations

import json
from pathlib import Path


TEST_FIRE_PATH = Path(__file__).resolve().parents[2] / "test_fire.geojson"

_test_fires: list[dict] = []


def _read_and_delete_file() -> list[dict]:
    try:
        data = json.loads(TEST_FIRE_PATH.read_text(encoding="utf-8"))
        TEST_FIRE_PATH.unlink()
        events = []
        for feature in data.get("features", []):
            props = feature.get("properties") or {}
            coords = (feature.get("geometry") or {}).get("coordinates", [])
            if len(coords) < 2:
                continue
            events.append({
                "latitude": float(coords[1]),
                "longitude": float(coords[0]),
                "brightness": props.get("brightness"),
                "scan": props.get("scan"),
                "track": props.get("track"),
                "acq_date": props.get("acq_date"),
                "acq_time": str(props.get("acq_time") or "").zfill(4),
                "satellite": "Teste",
                "confidence": props.get("confidence", "h"),
                "frp": props.get("frp", 75.0),
                "daynight": props.get("daynight", "D"),
            })
        print(f"[test_fire] {len(events)} foco(s) de teste carregado(s) e arquivo removido")
        return events
    except Exception as exc:
        print(f"[test_fire] Falha ao carregar: {exc}")
        return []


def load_and_consume_test_fires() -> list[dict]:
    """Called on each /api/fires request.

    If the file exists: loads and deletes it, caches the events.
    If the file is gone: clears the cache (fires disappear on this refresh).
    Returns the current cache.
    """
    global _test_fires
    if TEST_FIRE_PATH.exists():
        _test_fires = _read_and_delete_file()
    else:
        _test_fires = []
    return list(_test_fires)


def get_pending_test_fires() -> list[dict]:
    """Return cached test fires without mutating state.

    Used by /api/alerts/uc-fires so the UC alarm can trigger while the test
    fires are still visible on the map (between the /api/fires call that loaded
    them and the next one that clears them).
    """
    return list(_test_fires)
