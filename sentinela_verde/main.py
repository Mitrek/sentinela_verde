from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sentinela_verde.config import (
    DB_PATH,
    FETCH_DAYS,
    FETCH_INTERVAL_MINUTES,
    FIRMS_API_KEY,
    INPE_ENABLED,
    INPE_FETCH_INTERVAL_MINUTES,
    INPE_KML_URL,
    REGION_BBOX,
)
from sentinela_verde.db import get_recent_events, init_db, insert_fire_events
from sentinela_verde.geo.areas import (
    annotate_events_with_municipality,
    filter_events_by_area,
    filter_events_by_mg,
    get_area_by_id,
    get_area_geometry,
    get_mg_boundary_feature,
    load_areas,
)
from sentinela_verde.geo.conservation_units import (
    get_uc_fire_alert_groups,
    get_ucs_for_boundary,
    load_ucs,
)
from sentinela_verde.geo.map_renderer import render_map_html
from sentinela_verde.geo.operational_units import (
    filter_events_by_operational_unit,
    filter_events_by_operational_units,
    get_operational_unit,
    get_operational_unit_features,
    get_operational_unit_geometry,
    get_operational_units_features,
    get_operational_units_geometry,
    load_operational_units,
)
from sentinela_verde.services.firms import fetch_firms_data
from sentinela_verde.services.inpe import fetch_inpe_data
from sentinela_verde.services.test_fire import get_pending_test_fires, load_and_consume_test_fires


last_fetch_at: str | None = None
_fetch_tasks: list[asyncio.Task] = []

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DB_FILE_PATH = str((PROJECT_ROOT / DB_PATH).resolve()) if not Path(DB_PATH).is_absolute() else DB_PATH
WEB_DIR = BASE_DIR / "web"
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


def _get_map_events(hours: int = 48) -> list[dict]:
    return get_recent_events(DB_FILE_PATH, hours=hours)


def _resolve_selected_units(
    unit: str | None,
    units: list[str] | None,
) -> list[str]:
    resolved = []
    seen = set()
    for unit_id in units or []:
        if unit_id in seen or get_operational_unit(unit_id) is None:
            continue
        resolved.append(unit_id)
        seen.add(unit_id)

    if unit and unit not in seen and get_operational_unit(unit) is not None:
        resolved.append(unit)

    return resolved


def _filter_events_for_units(events: list[dict], selected_units: list[str]) -> list[dict]:
    if not selected_units:
        return filter_events_by_mg(events)
    if len(selected_units) == 1:
        return filter_events_by_operational_unit(events, selected_units[0])
    return filter_events_by_operational_units(events, selected_units)


async def _fetch_and_store_async() -> int:
    global last_fetch_at

    events = await fetch_firms_data(FIRMS_API_KEY, REGION_BBOX, FETCH_DAYS)
    inserted_count = insert_fire_events(DB_FILE_PATH, events)
    last_fetch_at = datetime.now(UTC).isoformat()

    return inserted_count


async def _fetch_and_store_inpe_async() -> int:
    events = await fetch_inpe_data(INPE_KML_URL)
    return insert_fire_events(DB_FILE_PATH, events)


async def _periodic_fetch(fetch_fn, interval_seconds: int, label: str) -> None:
    print(f"[scheduler] {label} task started, interval={interval_seconds}s", flush=True)
    while True:
        await asyncio.sleep(interval_seconds)
        print(f"[scheduler] {label} fetching", flush=True)
        try:
            await fetch_fn()
            print(f"[scheduler] {label} done", flush=True)
        except Exception as exc:
            print(f"[scheduler] {label} error: {exc}", flush=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _fetch_tasks

    init_db(DB_FILE_PATH)
    await _fetch_and_store_async()

    _fetch_tasks = [
        asyncio.create_task(
            _periodic_fetch(_fetch_and_store_async, FETCH_INTERVAL_MINUTES * 60, "FIRMS"),
            name="firms-fetch",
        )
    ]

    if INPE_ENABLED:
        await _fetch_and_store_inpe_async()
        _fetch_tasks.append(
            asyncio.create_task(
                _periodic_fetch(_fetch_and_store_inpe_async, INPE_FETCH_INTERVAL_MINUTES * 60, "INPE"),
                name="inpe-fetch",
            )
        )

    try:
        yield
    finally:
        for task in _fetch_tasks:
            task.cancel()
        await asyncio.gather(*_fetch_tasks, return_exceptions=True)


app = FastAPI(lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=str(WEB_DIR / "static"), check_dir=False),
    name="static",
)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/map", response_class=HTMLResponse)
async def get_map(
    area: str | None = Query(default=None),
    unit: str | None = Query(default=None),
) -> HTMLResponse:
    map_events = _get_map_events(hours=48)

    if unit is not None and get_operational_unit(unit) is not None:
        html = render_map_html(map_events, unit_id=unit)
        return HTMLResponse(content=html)

    if area is not None and get_area_by_id(area) is not None:
        html = render_map_html(map_events, area_id=area)
        return HTMLResponse(content=html)

    return HTMLResponse(content=render_map_html(map_events))


@app.get("/api/fires")
async def api_fires(
    hours: int = Query(default=48, ge=1),
    unit: str | None = Query(default=None),
    units: list[str] | None = Query(default=None),
) -> JSONResponse:
    events = get_recent_events(DB_FILE_PATH, hours=hours)
    events = _filter_events_for_units(events, _resolve_selected_units(unit, units))
    events = annotate_events_with_municipality(events)
    test_fires = load_and_consume_test_fires()
    if test_fires:
        test_fires = annotate_events_with_municipality(test_fires)
        events = test_fires + events
    return JSONResponse(events)


@app.get("/api/geojson/unit/{unit_id}")
async def api_geojson_unit(unit_id: str) -> JSONResponse:
    """GeoJSON FeatureCollection of municipality polygons for the selected unit."""
    features = get_operational_unit_features(unit_id)
    return JSONResponse({"type": "FeatureCollection", "features": features})


@app.get("/api/geojson/units")
async def api_geojson_units(
    unit: str | None = Query(default=None),
    units: list[str] | None = Query(default=None),
) -> JSONResponse:
    selected_units = _resolve_selected_units(unit, units)
    features = (
        get_operational_unit_features(selected_units[0])
        if len(selected_units) == 1
        else get_operational_units_features(selected_units)
    )
    return JSONResponse({"type": "FeatureCollection", "features": features})


@app.get("/api/geojson/ucs/{unit_id}")
async def api_geojson_ucs(unit_id: str) -> JSONResponse:
    """GeoJSON FeatureCollection of UC polygons that intersect the selected unit."""
    geometry = get_operational_unit_geometry(unit_id)
    features = get_ucs_for_boundary(unit_id, geometry)
    return JSONResponse({"type": "FeatureCollection", "features": features})


@app.get("/api/geojson/ucs")
async def api_geojson_ucs_units(
    unit: str | None = Query(default=None),
    units: list[str] | None = Query(default=None),
) -> JSONResponse:
    selected_units = _resolve_selected_units(unit, units)
    if len(selected_units) == 1:
        geometry = get_operational_unit_geometry(selected_units[0])
        boundary_id = selected_units[0]
    else:
        geometry = get_operational_units_geometry(selected_units)
        boundary_id = f"units:{'|'.join(selected_units)}"
    features = get_ucs_for_boundary(boundary_id, geometry)
    return JSONResponse({"type": "FeatureCollection", "features": features})


@app.get("/api/geojson/mg")
async def api_geojson_mg() -> JSONResponse:
    """GeoJSON FeatureCollection containing the Minas Gerais state outline."""
    feature = get_mg_boundary_feature()
    features = [feature] if feature is not None else []
    return JSONResponse({"type": "FeatureCollection", "features": features})


@app.get("/api/alerts/uc-fires")
async def api_uc_fire_alerts(
    after: str | None = Query(default=None),
    unit: str | None = Query(default=None),
    units: list[str] | None = Query(default=None),
) -> JSONResponse:
    """Grouped UC fire alerts for satellite acquisitions after the alarm cursor."""
    if not after or len(after) != 15 or "T" not in after:
        return JSONResponse([])

    events = get_recent_events(DB_FILE_PATH, hours=48)
    events = _filter_events_for_units(events, _resolve_selected_units(unit, units))
    pending_test = get_pending_test_fires()
    if pending_test:
        events = events + pending_test

    return JSONResponse(get_uc_fire_alert_groups(events, after))


@app.get("/api/status")
async def api_status(
    area: str | None = Query(default=None),
    unit: str | None = Query(default=None),
    units: list[str] | None = Query(default=None),
) -> JSONResponse:
    events = get_recent_events(DB_FILE_PATH, hours=48)
    selected_units = _resolve_selected_units(unit, units)
    if selected_units:
        events = _filter_events_for_units(events, selected_units)
    elif area and get_area_by_id(area) is not None:
        events = filter_events_by_area(events, area)
    else:
        events = filter_events_by_mg(events)
    return JSONResponse(
        {
            "last_fetch_at": last_fetch_at,
            "total_events": len(events),
            "scheduler_running": any(not t.done() for t in _fetch_tasks),
        }
    )


@app.get("/api/operational-units")
async def api_operational_units() -> JSONResponse:
    return JSONResponse(load_operational_units())


@app.get("/api/areas")
async def api_areas() -> JSONResponse:
    return JSONResponse(
        [
            {
                "id": area.get("id"),
                "name": area.get("name"),
                "region": area.get("region"),
                "hq": area.get("hq"),
            }
            for area in load_areas()
        ]
    )


@app.get("/api/ucs")
async def api_ucs() -> JSONResponse:
    return JSONResponse(load_ucs())



@app.post("/api/fetch")
async def api_fetch() -> JSONResponse:
    await _fetch_and_store_async()
    return JSONResponse({"triggered": True})
