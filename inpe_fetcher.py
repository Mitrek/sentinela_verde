from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

from areas import filter_events_by_mg


KML_NS = "http://www.opengis.net/kml/2.2"

_MODERATE_TIPOS = {"incêndio", "incendio"}


def _parse_description_fields(escaped_html: str) -> dict[str, str]:
    decoded = html.unescape(escaped_html)
    pairs = re.findall(
        r"<td[^>]*><b>([^<]+)</b></td>\s*<td[^>]*>(?:<b>)?([^<]*)(?:</b>)?</td>",
        decoded,
    )
    return {k.strip(): v.strip() for k, v in pairs}


def _parse_ultimo_foco(value: str) -> tuple[str | None, str | None]:
    try:
        dt = datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H%M")
    except ValueError:
        return None, None


def _placemark_to_event(placemark: ET.Element) -> dict | None:
    point = placemark.find(f".//{{{KML_NS}}}Point")
    if point is None:
        return None

    coords_el = point.find(f"{{{KML_NS}}}coordinates")
    if coords_el is None or not coords_el.text:
        return None

    try:
        parts = coords_el.text.strip().split(",")
        lon = float(parts[0])
        lat = float(parts[1])
    except (ValueError, IndexError):
        return None

    desc_el = placemark.find(f"{{{KML_NS}}}description")
    if desc_el is None or not desc_el.text:
        return None

    fields = _parse_description_fields(desc_el.text)

    if fields.get("Estado", "").upper() != "MINAS GERAIS":
        return None

    acq_date, acq_time = _parse_ultimo_foco(fields.get("Último foco", ""))
    if not acq_date or not acq_time:
        return None

    tipo = fields.get("Tipo", "").lower()
    frp = 50.0 if tipo in _MODERATE_TIPOS else None

    return {
        "latitude": lat,
        "longitude": lon,
        "brightness": None,
        "scan": None,
        "track": None,
        "acq_date": acq_date,
        "acq_time": acq_time,
        "satellite": "INPE",
        "confidence": "n",
        "frp": frp,
        "daynight": "",
    }


async def fetch_inpe_data(url: str) -> list[dict]:
    """Fetch INPE Queimadas active events KML and normalize to fire event dicts."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Failed to fetch INPE KML: {exc}")
        return []

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        print(f"Failed to parse INPE KML: {exc}")
        return []

    events = []
    for placemark in root.iter(f"{{{KML_NS}}}Placemark"):
        event = _placemark_to_event(placemark)
        if event is not None:
            events.append(event)

    return filter_events_by_mg(events)
