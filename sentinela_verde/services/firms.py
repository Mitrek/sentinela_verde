from __future__ import annotations

import asyncio
import csv
import io

import httpx
from apscheduler.schedulers.background import BackgroundScheduler


FIRMS_SOURCES = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"]

EXPECTED_COLUMNS = {
    "latitude",
    "longitude",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "confidence",
    "frp",
    "daynight",
}
BRIGHTNESS_COLUMNS = {"bright_ti4", "brightness"}


def _parse_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _map_row(row: dict[str, str]) -> dict:
    return {
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "brightness": _parse_float(row.get("bright_ti4") or row.get("brightness")),
        "scan": _parse_float(row.get("scan")),
        "track": _parse_float(row.get("track")),
        "acq_date": row.get("acq_date"),
        "acq_time": row.get("acq_time"),
        "satellite": row.get("satellite"),
        "confidence": row.get("confidence"),
        "frp": _parse_float(row.get("frp")),
        "daynight": row.get("daynight"),
    }


def _parse_csv(csv_text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text))
    fieldnames = set(reader.fieldnames or [])
    missing_columns = sorted(EXPECTED_COLUMNS - fieldnames)
    if missing_columns:
        raise ValueError(f"Missing expected columns: {missing_columns}")
    if not BRIGHTNESS_COLUMNS.intersection(fieldnames):
        raise ValueError("Missing expected brightness column: bright_ti4 or brightness")

    return [_map_row(row) for row in reader]


def _build_firms_url(api_key: str, source: str, bbox: str, days: int) -> str:
    return (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{api_key}/{source}/{bbox}/{days}"
    )


async def _fetch_source_data(
    client: httpx.AsyncClient, api_key: str, source: str, bbox: str, days: int
) -> list[dict]:
    url = _build_firms_url(api_key, source, bbox, days)

    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Failed to fetch FIRMS data from {source}: {exc}")
        return []

    try:
        return _parse_csv(response.text)
    except (ValueError, TypeError) as exc:
        print(f"Failed to parse FIRMS CSV from {source}: {exc}")
        return []


async def fetch_firms_data(api_key: str, bbox: str, days: int) -> list[dict]:
    """
    GET https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/{source}/{bbox}/{days}

    Parse the CSV response. Map columns to FireEvent fields:
      bright_ti4 / brightness → brightness
      (all others map directly by name)

    On HTTP error (4xx, 5xx): log with print(), return []
    On CSV parse error: log with print(), return []
    Never raise — scheduler must not crash.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        results = await asyncio.gather(
            *[
                _fetch_source_data(client, api_key, source, bbox, days)
                for source in FIRMS_SOURCES
            ]
        )

    merged_events: list[dict] = []
    for source_events in results:
        merged_events.extend(source_events)

    return merged_events


def start_scheduler(fetch_and_store_fn, interval_minutes: int) -> BackgroundScheduler:
    """
    Start APScheduler BackgroundScheduler.
    Schedule fetch_and_store_fn to run every interval_minutes minutes.
    fetch_and_store_fn is a sync function (wrap async inside it with asyncio.run).
    Return the scheduler instance.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        fetch_and_store_fn,
        trigger="interval",
        minutes=interval_minutes,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler
