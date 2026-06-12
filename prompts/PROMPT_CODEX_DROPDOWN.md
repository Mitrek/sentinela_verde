# Codex Prompt — Fire Catcher: Area Dropdown Feature

You are adding an **area filter dropdown** to Fire Catcher.  
The dropdown lets the user choose a CBMMG Operational Command (COB) region, and the map zooms to that area showing only its fires — with municipality outlines drawn from a GeoJSON file.

Do not touch `config.py`, `deploy/`, or `tests/`.

---

## Context: what already exists

- `map_renderer.py` — renders a Folium map and **saves it to a static HTML file**
- `main.py` — serves `/map` by reading that static file; has `last_fetch_at` global, scheduler, lifespan
- `db.py` — `get_recent_events(db_path, hours)` returns `list[dict]`
- `articulation/areas.json` — COB definitions: each has `id`, `name`, `region`, `hq`, `units`, `municipios` (list of municipality names)
- `shapefiles/MG_Municipios_2025.geojson` — GeoJSON FeatureCollection, 853 features. Each feature has a `properties` object. **Before writing code, inspect the first feature's properties keys** by loading the file and printing `list(features[0]["properties"].keys())`. The municipality name field is likely `NM_MUN` (IBGE standard), but verify. Use whatever key you find.

---

## Your deliverables (in order)

1. `areas.py` — new module
2. `map_renderer.py` — modify existing
3. `main.py` — modify existing
4. `templates/index.html` — modify existing

---

## 1. `areas.py` (new file)

This module loads the COB definitions and GeoJSON, builds Shapely geometries, and exposes filtering functions.

```python
# areas.py

import json
from pathlib import Path
from shapely.geometry import shape, Point
from shapely.ops import unary_union

AREAS_JSON_PATH = Path(__file__).parent / "articulation" / "areas.json"
GEOJSON_PATH = Path(__file__).parent / "shapefiles" / "MG_Municipios_2025.geojson"
```

**Functions to implement:**

```python
def load_areas() -> list[dict]:
    """
    Return the list of COB dicts from areas.json.
    Each dict has: id, name, region, hq, units, municipios.
    Cache the result in a module-level variable after first load.
    """

def get_area_by_id(area_id: str) -> dict | None:
    """Return the COB dict for the given id (e.g. '1COB'), or None if not found."""

def get_area_geometry(area_id: str) -> object | None:
    """
    Return a Shapely geometry (unary_union of municipality polygons) for the given COB.

    Steps:
    1. Load areas.json → find the COB with matching id → get its `municipios` list
    2. Load the GeoJSON file
    3. Inspect the municipality name property key (likely NM_MUN — verify at runtime)
    4. For each GeoJSON feature whose name is in the COB's `municipios` list,
       build a Shapely geometry via shape(feature["geometry"])
    5. Return unary_union of all matched geometries

    Cache geometries per area_id in a module-level dict after first computation.
    On any error: print the error and return None.
    """

def filter_events_by_area(events: list[dict], area_id: str) -> list[dict]:
    """
    Return only the events whose (latitude, longitude) falls within
    the Shapely geometry of the given area_id.
    If geometry is None (load error), return all events unchanged.
    """

def get_area_bounds(area_id: str) -> tuple[float, float, float, float] | None:
    """
    Return (min_lat, min_lon, max_lat, max_lon) bounding box of the area geometry.
    Returns None if geometry is unavailable.
    Used by map_renderer to fit the map to the selected area.
    """
```

**Important:**
- Use module-level caches (a dict for geometries, a variable for the areas list) so files are only read once
- Never raise — catch all exceptions, print them, return safe fallbacks

---

## 2. `map_renderer.py` — modify existing

Add a new function alongside the existing `render_map`. Do not change `render_map`'s signature or behavior.

```python
def render_map_html(events: list[dict], area_id: str | None = None) -> str:
    """
    Like render_map, but returns the HTML string instead of saving to a file.
    Accepts an optional area_id to filter and zoom.

    If area_id is provided and valid:
      1. Import areas module and call filter_events_by_area(events, area_id)
      2. Get bounds via get_area_bounds(area_id); if available, fit the map to those bounds
         using folium.Map(location=center_of_bounds, zoom_start=7)
      3. Draw municipality outlines for the selected COB using folium.GeoJson:
         - Load the GeoJSON, keep only features in the COB's municipios list
         - Style: no fill (fill_opacity=0), border color="#e67e22", weight=1
         - Add as a layer to the map
      4. Compute center from filtered events; if no events, use center of bounds

    If area_id is None or not found:
      - Behave exactly like render_map but return HTML string

    Fire markers use the same color logic and popup as render_map.
    Return fire_map.get_root().render() as a string.
    """
```

**Note on zoom:** When area_id is provided and bounds are available, compute center as
`((min_lat + max_lat) / 2, (min_lon + max_lon) / 2)` and use `zoom_start=7`.
For "All MG" (no area_id), keep the existing behavior from `render_map`.

---

## 3. `main.py` — modify existing

### New import
```python
from areas import load_areas, get_area_by_id
```

### New endpoint: `GET /api/areas`

```python
@app.get("/api/areas")
async def api_areas() -> JSONResponse:
    """
    Return the list of COBs for populating the dropdown.
    Each item: { id, name, region, hq }
    (omit the full municipios list — not needed by the frontend)
    """
```

### Modify: `GET /map`

Change the `/map` endpoint to accept an optional `area` query parameter and render on-demand:

```python
@app.get("/map", response_class=HTMLResponse)
async def get_map(area: str | None = Query(default=None)) -> HTMLResponse:
    """
    If area is None: serve the pre-rendered static map.html (existing behavior).
    If area is set: render on-demand using render_map_html(recent_events, area_id=area)
      and return the result as HTMLResponse.
    Validate area: if get_area_by_id(area) is None, ignore it (treat as None).
    """
```

For the on-demand render, fetch recent events:
```python
recent_events = get_recent_events(DB_FILE_PATH, hours=48)
html = render_map_html(recent_events, area_id=area)
return HTMLResponse(content=html)
```

Do not change `/api/fetch`, the lifespan, or `fetch_and_store`.

---

## 4. `templates/index.html` — modify existing

### What to add

**A `<select>` dropdown** in the status bar, between the status info and the Refresh button.

The dropdown has:
- A first option: `<option value="">All Minas Gerais</option>`
- Options for each COB, populated from `/api/areas` on page load
- Format: `<option value="1COB">1º COB – Belo Horizonte (Região Central)</option>`

When the selection changes, the iframe `src` updates to:
- `/map` if value is `""` (All MG)
- `/map?area=1COB` (or whichever COB)

Append a cache-buster `&t=<timestamp>` (or `?t=<timestamp>` for All MG) to force iframe reload.

### Status bar layout after change

```
| Last updated: ...   N fire events   [dropdown▼]   [Refresh] |
```

The dropdown sits between the event count and the Refresh button.

### CSS for the dropdown

Match the dark theme:
```css
#area-select {
    background-color: #2a2a2a;
    color: #eeeeee;
    border: 1px solid #444;
    padding: 4px 8px;
    border-radius: 3px;
    font-size: 13px;
    cursor: pointer;
}
#area-select:focus {
    outline: none;
    border-color: #c0392b;
}
```

### JS: populate dropdown on load

```javascript
async function loadAreas() {
    try {
        const response = await fetch('/api/areas');
        const areas = await response.json();
        const select = document.getElementById('area-select');
        areas.forEach(area => {
            const opt = document.createElement('option');
            opt.value = area.id;
            opt.textContent = `${area.name} (${area.region})`;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load areas', e);
    }
}
```

### JS: handle dropdown change

```javascript
document.getElementById('area-select').addEventListener('change', function () {
    const area = this.value;
    const base = '/map';
    const t = new Date().getTime();
    mapFrame.src = area
        ? `${base}?area=${encodeURIComponent(area)}&t=${t}`
        : `${base}?t=${t}`;
});
```

### Also update `handleRefresh`

When the user clicks Refresh, reload the iframe with the **currently selected area** preserved:
```javascript
const area = document.getElementById('area-select').value;
const base = '/map';
const t = new Date().getTime();
mapFrame.src = area
    ? `${base}?area=${encodeURIComponent(area)}&t=${t}`
    : `${base}?t=${t}`;
```

---

## Rules

- Do not modify `config.py`, `db.py`, `fetcher.py`, or anything in `deploy/` or `tests/`
- Do not add dependencies beyond those already in `requirements.txt`
  (`shapely` is already listed — use it; `json` and `pathlib` are stdlib)
- `areas.py` must never raise — all exceptions caught and logged with `print()`
- `render_map_html` must never raise — fallback to full-MG render if area processing fails
- The existing `render_map(events, output_path)` function must remain unchanged
- Keep functions small and focused
- Use `print()` for logging (no logging module)
- If the GeoJSON property key for municipality name is not `NM_MUN`, adapt accordingly — inspect at runtime as instructed
