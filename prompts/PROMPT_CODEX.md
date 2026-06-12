# Codex Prompt — Fire Catcher

You are implementing the backend of a Python web app called **Fire Catcher**.  
It fetches NASA FIRMS fire detection data and displays active fires on an interactive map.  
You are responsible for all `[CODEX]`-tagged modules. Do not touch `[GEMINI]` files.

---

## Your deliverables (in order)

1. `db.py`
2. `fetcher.py`
3. `map_renderer.py`
4. `main.py`
5. `tests/test_db.py`
6. `tests/test_fetcher.py`

Implement them in that order. Each one depends on the previous.

---

## Stack constraints

- Python 3.11+
- FastAPI `^0.111`, Uvicorn `^0.29`, APScheduler `^3.10`
- `httpx ^0.27` for async HTTP
- `folium ^0.16` for map rendering
- `sqlite3` from stdlib only — no SQLAlchemy, no ORM
- `python-dotenv ^1.0` (already handled in `config.py` — just import from it)
- No extra dependencies beyond these

---

## `config.py` interface (already written by Gemini — just import from it)

```python
from config import (
    FIRMS_API_KEY,
    REGION_BBOX,
    FETCH_DAYS,
    FETCH_INTERVAL_MINUTES,
    DB_PATH,
    MAP_OUTPUT_PATH,
    HOST,
    PORT,
)
```

---

## 1. `db.py`

Pure SQLite, no ORM.

**Table schema:**

```sql
CREATE TABLE IF NOT EXISTS fire_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    brightness REAL,
    scan REAL,
    track REAL,
    acq_date TEXT,
    acq_time TEXT,
    satellite TEXT,
    confidence TEXT,
    frp REAL,
    daynight TEXT,
    fetched_at TEXT NOT NULL,
    UNIQUE(latitude, longitude, acq_date, acq_time, satellite)
);
```

**Functions to implement:**

```python
def init_db(db_path: str) -> None:
    """Create fire_events table if not exists."""

def insert_fire_events(db_path: str, events: list[dict]) -> int:
    """
    Insert list of fire event dicts.
    Use INSERT OR IGNORE to skip duplicates silently.
    Set fetched_at to current UTC ISO datetime on insert.
    Return count of newly inserted rows.
    """

def get_recent_events(db_path: str, hours: int = 48) -> list[dict]:
    """Return all events with fetched_at within the last `hours` hours as list of dicts."""

def get_all_events(db_path: str) -> list[dict]:
    """Return all stored events as list of dicts."""
```

---

## 2. `fetcher.py`

```python
async def fetch_firms_data(api_key: str, bbox: str, days: int) -> list[dict]:
    """
    GET https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/VIIRS_SNPP_NRT/{bbox}/{days}

    Parse the CSV response. Map columns to FireEvent fields:
      bright_ti4  → brightness
      (all others map directly by name)

    On HTTP error (4xx, 5xx): log with print(), return []
    On CSV parse error: log with print(), return []
    Never raise — scheduler must not crash.
    """

def start_scheduler(fetch_and_store_fn, interval_minutes: int) -> BackgroundScheduler:
    """
    Start APScheduler BackgroundScheduler.
    Schedule fetch_and_store_fn to run every interval_minutes minutes.
    fetch_and_store_fn is a sync function (wrap async inside it with asyncio.run).
    Return the scheduler instance.
    """
```

---

## 3. `map_renderer.py`

```python
def render_map(events: list[dict], output_path: str) -> None:
    """
    Render a Folium map.

    Center: centroid of all event lat/lons.
    Fallback if no events: center=(-15.0, -55.0), zoom=4.

    Each event → folium.CircleMarker:
      radius=5, fill=True, fill_opacity=0.7
      color + fill_color:
        frp > 100  → "red"
        frp > 30   → "orange"
        else       → "yellow"
      popup HTML: acq_date, acq_time, frp MW, satellite, confidence

    Save as HTML to output_path.
    """
```

---

## 4. `main.py`

FastAPI app with lifespan.

**Routes:**

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/` | Return `TemplateResponse("index.html")` via Jinja2 |
| `GET` | `/map` | Return `map.html` contents as `HTMLResponse` |
| `GET` | `/api/fires` | JSON list of recent events, accepts `?hours=N` (default 48) |
| `GET` | `/api/status` | JSON: `last_fetch_at`, `total_events`, `scheduler_running` |
| `POST` | `/api/fetch` | Trigger immediate fetch + re-render map, return `{"triggered": true}` |

**Lifespan (startup sequence):**
1. `init_db(DB_PATH)`
2. Run one immediate fetch + store + render
3. Start scheduler

**Static + templates:**
- Mount `StaticFiles` at `/static` from `./static/`
- Jinja2Templates from `./templates/`

**Global state** (module-level):
```python
last_fetch_at: str | None = None
scheduler: BackgroundScheduler | None = None
```

The `fetch_and_store` function (called by scheduler and `/api/fetch`) should:
1. Call `fetch_firms_data()`
2. Call `insert_fire_events()`
3. Call `render_map()` with `get_recent_events()`
4. Update `last_fetch_at`

---

## 5. `tests/test_db.py`

- Use `tmp_path` pytest fixture for DB path
- Test `init_db` creates the `fire_events` table
- Test `insert_fire_events` inserts a sample event and returns count = 1
- Test duplicate insert returns count = 0 and table still has 1 row
- Test `get_recent_events` returns inserted event when within time window
- Test `get_recent_events` returns nothing if `fetched_at` is older than the hours window

---

## 6. `tests/test_fetcher.py`

- Use `pytest-asyncio` and `respx` (or `unittest.mock`) to mock `httpx.AsyncClient.get`
- Test `fetch_firms_data` with a valid mock CSV response returns correct list of dicts
- Test `fetch_firms_data` returns `[]` on HTTP 500
- Test `fetch_firms_data` returns `[]` on malformed CSV (no expected columns)

Sample mock CSV to use in tests:
```
latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight
-10.123,-55.456,320.5,0.39,0.36,2026-06-04,1420,N,nominal,2.0NRT,290.1,45.2,D
```

---

## Rules

- If a behavior is unclear, leave a `# TODO: clarify with Claude —` comment and implement a reasonable default
- Do not modify `config.py`, `templates/index.html`, or anything in `deploy/`
- Do not add dependencies not listed in the stack
- Keep functions small and focused — no god functions
- Use `print()` for logging (no logging module needed for MVP)
