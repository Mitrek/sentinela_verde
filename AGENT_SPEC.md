# Fire Catcher — Agent Build Specification

**Project**: Fire Catcher  
**Purpose**: Python web app that periodically fetches NASA FIRMS fire detection data for a defined geographic region and displays active fires on an interactive map.  
**Host**: Hetzner CX11 (Ubuntu 22.04)  
**Spec author**: Claude (Anthropic) — architecture and review role  

---

## Agent Roles

This project is built collaboratively by three agents. Each section of this spec is tagged with the agent responsible for it.

| Tag | Agent | Strength applied |
|---|---|---|
| `[CODEX]` | OpenAI Codex | Feature implementation, API logic, tests |
| `[GEMINI]` | Google Gemini | Configuration, deployment, templates, repetitive tasks |
| `[CLAUDE]` | Anthropic Claude | Architecture, data modeling, review, complex logic |

No agent should rewrite another's output without a correction note from Claude in `REVIEW_NOTES.md`.

---

## Project Structure

```
fire_catcher/
├── main.py               # [CODEX]
├── fetcher.py            # [CODEX]
├── models.py             # [CLAUDE spec] → [CODEX build]
├── db.py                 # [CODEX]
├── map_renderer.py       # [CODEX]
├── config.py             # [GEMINI]
├── templates/
│   └── index.html        # [GEMINI]
├── static/               # [GEMINI] — served by Nginx
├── deploy/
│   ├── nginx.conf        # [GEMINI]
│   ├── fire_catcher.service  # [GEMINI]
│   └── deploy.sh         # [GEMINI]
├── tests/
│   ├── test_fetcher.py   # [CODEX]
│   └── test_db.py        # [CODEX]
├── requirements.txt      # [GEMINI] — derived from this spec
└── AGENT_SPEC.md         # this file
```

---

## Stack

| Layer | Library | Version |
|---|---|---|
| Web framework | FastAPI | ^0.111 |
| ASGI server | Uvicorn | ^0.29 |
| Scheduler | APScheduler | ^3.10 |
| Database | SQLite via `sqlite3` (stdlib) | — |
| Map rendering | Folium | ^0.16 |
| HTTP client | httpx | ^0.27 |
| Config | python-dotenv | ^1.0 |
| Testing | pytest + httpx | latest |

---

## Data Model `[CLAUDE]`

### `FireEvent` (stored in SQLite)

```python
@dataclass
class FireEvent:
    id: int                  # autoincrement primary key
    latitude: float          # from FIRMS
    longitude: float         # from FIRMS
    brightness: float        # brightness temperature (Kelvin), FIRMS field `brightness`
    scan: float              # along-scan pixel size
    track: float             # along-track pixel size
    acq_date: str            # acquisition date, ISO format YYYY-MM-DD
    acq_time: str            # acquisition time HHMM UTC
    satellite: str           # e.g. "Terra", "Aqua", "N" (NOAA-20)
    confidence: str          # "low", "nominal", "high" (VIIRS) or int string (MODIS)
    frp: float               # Fire Radiative Power (MW)
    daynight: str            # "D" or "N"
    fetched_at: str          # ISO datetime when our system stored this record
```

**SQLite table name**: `fire_events`  
**Unique constraint**: `(latitude, longitude, acq_date, acq_time, satellite)` — prevents duplicate inserts on repeated fetches.

---

## NASA FIRMS API `[CLAUDE]`

### Registration
API key required. Free tier. Register at: https://firms.modaps.eosdis.nasa.gov/api/area/

### Endpoint used

```
GET https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/{BBOX}/{DAYS}
```

- `MAP_KEY`: API key from env var `FIRMS_API_KEY`
- `VIIRS_SNPP_NRT`: near-real-time VIIRS data (also supports `MODIS_NRT`)
- `BBOX`: `west,south,east,north` — e.g. `-74.0,-34.0,-34.0,5.5` (Brazil)
- `DAYS`: integer 1–10

### Response format
CSV. Relevant columns: `latitude`, `longitude`, `bright_ti4`, `scan`, `track`, `acq_date`, `acq_time`, `satellite`, `confidence`, `version`, `bright_ti5`, `frp`, `daynight`

### Mapping CSV → FireEvent

| CSV column | FireEvent field |
|---|---|
| `latitude` | `latitude` |
| `longitude` | `longitude` |
| `bright_ti4` | `brightness` |
| `scan` | `scan` |
| `track` | `track` |
| `acq_date` | `acq_date` |
| `acq_time` | `acq_time` |
| `satellite` | `satellite` |
| `confidence` | `confidence` |
| `frp` | `frp` |
| `daynight` | `daynight` |

---

## Module Specifications

---

### `config.py` `[GEMINI]`

Read all configuration from environment variables (`.env` file via `python-dotenv`).

```python
# config.py — load and expose these values

FIRMS_API_KEY: str         # required, no default
REGION_BBOX: str           # default "-74.0,-34.0,-34.0,5.5"  (covers Brazil)
FETCH_DAYS: int            # default 1
FETCH_INTERVAL_MINUTES: int  # default 60
DB_PATH: str               # default "fire_catcher.db"
MAP_OUTPUT_PATH: str       # default "static/map.html"
HOST: str                  # default "0.0.0.0"
PORT: int                  # default 8000
```

Raise a clear `ValueError` at startup if `FIRMS_API_KEY` is missing.

---

### `db.py` `[CODEX]`

Pure SQLite, no ORM. Expose these functions:

```python
def init_db(db_path: str) -> None:
    """Create fire_events table if not exists. Apply unique constraint."""

def insert_fire_events(db_path: str, events: list[dict]) -> int:
    """
    Insert list of fire event dicts. Skip duplicates silently (INSERT OR IGNORE).
    Return count of newly inserted rows.
    """

def get_recent_events(db_path: str, hours: int = 48) -> list[dict]:
    """Return all events with fetched_at within the last `hours` hours."""

def get_all_events(db_path: str) -> list[dict]:
    """Return all stored events."""
```

Use `sqlite3` from stdlib only. No SQLAlchemy.

---

### `fetcher.py` `[CODEX]`

```python
async def fetch_firms_data(api_key: str, bbox: str, days: int) -> list[dict]:
    """
    Fetch CSV from FIRMS API using httpx async client.
    Parse CSV into list of dicts matching FireEvent fields.
    On HTTP error: log the error, return empty list (do not crash the scheduler).
    On CSV parse error: log and return empty list.
    """

def start_scheduler(fetch_fn, interval_minutes: int) -> None:
    """
    Start APScheduler BackgroundScheduler.
    Runs fetch_fn every `interval_minutes` minutes.
    fetch_fn is a coroutine — wrap with asyncio.run() if needed.
    """
```

The scheduler must start **after** the FastAPI app is fully initialized (use `lifespan` context manager in `main.py`).

---

### `map_renderer.py` `[CODEX]`

```python
def render_map(events: list[dict], output_path: str) -> None:
    """
    Render a Folium map centered on the centroid of all events.
    If no events: center on Brazil (-15.0, -55.0), zoom 4.
    
    Each fire point:
      - CircleMarker, radius=5
      - color: red if frp > 100, orange if frp > 30, yellow otherwise
      - Popup: acq_date, acq_time, frp, satellite, confidence
    
    Save to output_path as HTML file.
    """
```

---

### `main.py` `[CODEX]`

FastAPI app. Routes:

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serve `index.html` (which embeds the map iframe) |
| `GET` | `/map` | Return the rendered `map.html` as HTML response |
| `GET` | `/api/fires` | JSON — recent fire events (last 48h by default) |
| `GET` | `/api/fires?hours=N` | JSON — events from last N hours |
| `GET` | `/api/status` | JSON — last fetch time, total events in DB, scheduler status |
| `POST` | `/api/fetch` | Trigger a manual fetch (no auth needed for MVP) |

**Lifespan**: on startup → `init_db()`, start scheduler, do one immediate fetch, render initial map.

Mount `static/` as StaticFiles at `/static`.

---

### `templates/index.html` `[GEMINI]`

Simple HTML page. Requirements:
- Title: "Fire Catcher"
- Embeds `/map` in a full-viewport `<iframe>`
- Small status bar at top showing last updated time (fetch from `/api/status` via `fetch()`)
- "Refresh Map" button that calls `POST /api/fetch` then reloads the iframe
- No frontend framework. Vanilla JS only.
- Dark background (`#111`), white text, minimal styling

---

## Deployment `[GEMINI]`

### `requirements.txt`
Generate from the stack table above. Pin major versions.

### `deploy/fire_catcher.service` (systemd)
- `WorkingDirectory`: `/opt/fire_catcher`
- `ExecStart`: `uvicorn main:app --host 0.0.0.0 --port 8000`
- `Restart=always`
- `EnvironmentFile`: `/opt/fire_catcher/.env`
- Run as user `firecatcher` (non-root)

### `deploy/nginx.conf`
- Reverse proxy: `localhost:8000` → public port 80
- Gzip enabled
- Static files served directly by Nginx from `/opt/fire_catcher/static/`
- Set `proxy_read_timeout 60s`

### `deploy/deploy.sh`
Script that:
1. Creates user `firecatcher`
2. Copies project to `/opt/fire_catcher`
3. Creates virtualenv, installs requirements
4. Copies `.service` and `nginx.conf` to correct system paths
5. Enables and starts both services
6. Prints final status

---

## Tests `[CODEX]`

### `tests/test_fetcher.py`
- Mock `httpx.AsyncClient.get` to return a sample CSV string
- Assert `fetch_firms_data` returns correctly parsed list of dicts
- Assert empty list returned on HTTP 4xx/5xx

### `tests/test_db.py`
- Use a temp file for the DB path
- Test `init_db` creates the table
- Test `insert_fire_events` inserts and returns correct count
- Test duplicate insert is silently ignored (count = 0)
- Test `get_recent_events` filters by time correctly

---

## Inter-Agent Handoff Protocol

1. **Claude** writes or updates this spec
2. **Codex** reads `[CODEX]`-tagged sections and implements them
3. **Gemini** reads `[GEMINI]`-tagged sections and produces those files
4. When Codex or Gemini is unsure about intent: do not guess — leave a `# TODO: clarify with Claude —` comment and proceed with the rest
5. **Claude** reviews output files and writes correction notes to `REVIEW_NOTES.md` if needed
6. No agent modifies another agent's output without a note in `REVIEW_NOTES.md`

---

## MVP Definition of Done

- [ ] App starts without errors with a valid `FIRMS_API_KEY` in `.env`
- [ ] Scheduler fetches data every 60 minutes automatically
- [ ] Map renders with fire points colored by FRP
- [ ] `/api/fires` returns valid JSON
- [ ] `/api/status` shows last fetch time
- [ ] Manual fetch via "Refresh Map" button works
- [ ] App survives a restart (data persisted in SQLite)
- [ ] Systemd service starts on Hetzner boot
- [ ] Nginx proxies correctly on port 80

---

*Last updated by Claude — 2026-06-04*
