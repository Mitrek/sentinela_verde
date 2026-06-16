# Sentinela Verde

FastAPI + Leaflet application for monitoring satellite fire detections in Minas Gerais.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env  # if you create one locally
```

Required environment:

```text
FIRMS_API_KEY=<nasa-firms-api-key>
```

Optional environment:

```text
REGION_BBOX=-74.0,-34.0,-34.0,5.5
FETCH_DAYS=1
FETCH_INTERVAL_MINUTES=60
DB_PATH=fire_catcher.db
INPE_ENABLED=true
INPE_FETCH_INTERVAL_MINUTES=10
```

## Run

```bash
./run.sh
```

The app runs at `http://localhost:8000`.

## Test

```bash
python -m pytest
node --check sentinela_verde/web/static/js/app.js
```

## Data

Runtime geodata lives under `sentinela_verde/data/geojson/`. The simplified municipality layer used by the frontend can be regenerated with:

```bash
python scripts/build_simplified_municipalities.py
```
