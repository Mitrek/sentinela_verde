from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from areas import (
    filter_events_by_area,
    get_area_bounds,
    get_area_by_id,
    get_area_geometry,
    load_areas,
)
from config import (
    DB_PATH,
    FETCH_DAYS,
    FETCH_INTERVAL_MINUTES,
    FIRMS_API_KEY,
    MAP_OUTPUT_PATH,
    REGION_BBOX,
)
from conservation_units import get_uc_feature, load_ucs
from db import get_all_events, get_recent_events, init_db, insert_fire_events
from fetcher import fetch_firms_data, start_scheduler
from map_renderer import render_map, render_map_html


last_fetch_at: str | None = None
scheduler: BackgroundScheduler | None = None

BASE_DIR = Path(__file__).resolve().parent
DB_FILE_PATH = str((BASE_DIR / DB_PATH).resolve()) if not Path(DB_PATH).is_absolute() else DB_PATH
MAP_FILE_PATH = (
    str((BASE_DIR / MAP_OUTPUT_PATH).resolve())
    if not Path(MAP_OUTPUT_PATH).is_absolute()
    else MAP_OUTPUT_PATH
)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _get_map_events(hours: int = 48) -> list[dict]:
    recent_events = get_recent_events(DB_FILE_PATH, hours=hours)
    if recent_events:
        return recent_events

    # TODO: Remove this fallback once live fetches reliably keep the 48h window populated.
    return get_all_events(DB_FILE_PATH)


async def _fetch_and_store_async() -> int:
    global last_fetch_at

    events = await fetch_firms_data(FIRMS_API_KEY, REGION_BBOX, FETCH_DAYS)
    inserted_count = insert_fire_events(DB_FILE_PATH, events)
    render_map(_get_map_events(), MAP_FILE_PATH)
    last_fetch_at = datetime.now(UTC).isoformat()

    return inserted_count


def fetch_and_store() -> int:
    return asyncio.run(_fetch_and_store_async())


@asynccontextmanager
async def lifespan(_: FastAPI):
    global scheduler

    init_db(DB_FILE_PATH)
    await _fetch_and_store_async()
    scheduler = start_scheduler(fetch_and_store, FETCH_INTERVAL_MINUTES)

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static"), check_dir=False),
    name="static",
)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/map", response_class=HTMLResponse)
async def get_map(
    area: str | None = Query(default=None),
    uc: str | None = Query(default=None),
) -> HTMLResponse:
    map_events = _get_map_events(hours=48)

    if uc is not None and get_uc_feature(uc) is not None:
        html = render_map_html(map_events, uc_id=uc)
        return HTMLResponse(content=html)

    if area is not None and get_area_by_id(area) is not None:
        html = render_map_html(map_events, area_id=area)
        return HTMLResponse(content=html)

    return HTMLResponse(content=render_map_html(map_events))


@app.get("/api/fires")
async def api_fires(hours: int = Query(default=48, ge=1)) -> JSONResponse:
    return JSONResponse(get_recent_events(DB_FILE_PATH, hours=hours))


@app.get("/api/status")
async def api_status() -> JSONResponse:
    return JSONResponse(
        {
            "last_fetch_at": last_fetch_at,
            "total_events": len(get_all_events(DB_FILE_PATH)),
            "scheduler_running": bool(scheduler and scheduler.running),
        }
    )


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


@app.get("/api/debug/area/{area_id}")
async def api_debug_area(area_id: str) -> JSONResponse:
    recent_events = get_recent_events(DB_FILE_PATH, hours=48)
    geometry = get_area_geometry(area_id)

    return JSONResponse(
        {
            "total_recent_events": len(recent_events),
            "total_all_events": len(get_all_events(DB_FILE_PATH)),
            "sample_event": recent_events[0] if recent_events else None,
            "geometry_built": geometry is not None,
            "geometry_bounds": get_area_bounds(area_id) if geometry is not None else None,
            "events_after_filter": len(filter_events_by_area(recent_events, area_id)),
        }
    )


@app.post("/api/fetch")
async def api_fetch() -> JSONResponse:
    await _fetch_and_store_async()
    return JSONResponse({"triggered": True})
