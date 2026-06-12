# Gemini Prompt — Fire Catcher

You are handling configuration, templates, and deployment for a Python web app called **Fire Catcher**.  
It fetches NASA FIRMS fire detection data and displays active fires on an interactive map.  
You are responsible for all `[GEMINI]`-tagged files. Do not touch Python source files in the project root.

---

## Your deliverables (produce all of them)

1. `config.py`
2. `.env.example`
3. `requirements.txt`
4. `templates/index.html`
5. `deploy/fire_catcher.service`
6. `deploy/nginx.conf`
7. `deploy/deploy.sh`

---

## Stack (for requirements.txt)

| Library | Version |
|---|---|
| fastapi | ^0.111 |
| uvicorn[standard] | ^0.29 |
| apscheduler | ^3.10 |
| httpx | ^0.27 |
| folium | ^0.16 |
| python-dotenv | ^1.0 |
| jinja2 | ^3.1 |
| pytest | latest |
| pytest-asyncio | latest |

---

## 1. `config.py`

Read all values from environment using `python-dotenv`. Expose them as module-level constants.

```python
# config.py
from dotenv import load_dotenv
import os

load_dotenv()

FIRMS_API_KEY: str = os.getenv("FIRMS_API_KEY", "")
REGION_BBOX: str   = os.getenv("REGION_BBOX", "-74.0,-34.0,-34.0,5.5")
FETCH_DAYS: int    = int(os.getenv("FETCH_DAYS", "1"))
FETCH_INTERVAL_MINUTES: int = int(os.getenv("FETCH_INTERVAL_MINUTES", "60"))
DB_PATH: str       = os.getenv("DB_PATH", "fire_catcher.db")
MAP_OUTPUT_PATH: str = os.getenv("MAP_OUTPUT_PATH", "static/map.html")
HOST: str          = os.getenv("HOST", "0.0.0.0")
PORT: int          = int(os.getenv("PORT", "8000"))

if not FIRMS_API_KEY:
    raise ValueError("FIRMS_API_KEY is required. Set it in your .env file.")
```

Write this exactly. Other modules import from here.

---

## 2. `.env.example`

```env
# Get your free API key at: https://firms.modaps.eosdis.nasa.gov/api/area/
FIRMS_API_KEY=your_api_key_here

# Bounding box: west,south,east,north
# Default covers Brazil
REGION_BBOX=-74.0,-34.0,-34.0,5.5

# How many days of data to fetch (1–10)
FETCH_DAYS=1

# How often to fetch, in minutes
FETCH_INTERVAL_MINUTES=60

# File paths (relative to project root)
DB_PATH=fire_catcher.db
MAP_OUTPUT_PATH=static/map.html

# Server
HOST=0.0.0.0
PORT=8000
```

---

## 3. `requirements.txt`

Pin exact minor versions. Use the stack table above.  
Output valid pip `requirements.txt` format.

---

## 4. `templates/index.html`

Requirements:
- Title: `Fire Catcher`
- Full-viewport `<iframe>` embedding `/map` (width 100%, height 100vh minus the status bar)
- Status bar at the top (height ~40px), dark background `#1a1a1a`, white text
  - Shows: `Last updated: <timestamp>` (fetched from `/api/status` → field `last_fetch_at`)
  - Shows: `<N> fire events` (fetched from `/api/status` → field `total_events`)
  - "Refresh" button on the right side
- Clicking "Refresh":
  1. POST to `/api/fetch`
  2. Wait for response
  3. Reload the iframe (`document.getElementById('map-frame').src += ''`)
  4. Update status bar with fresh `/api/status`
- No frontend framework. Vanilla JS only.
- `<meta>` viewport tag for mobile
- Auto-refresh status bar every 5 minutes (setInterval)

Color palette:
```
background:  #111111
bar bg:      #1a1a1a
bar text:    #eeeeee
button bg:   #c0392b
button hover:#e74c3c
button text: #ffffff
```

---

## 5. `deploy/fire_catcher.service`

Systemd unit file.

Requirements:
- Description: `Fire Catcher Web App`
- After: `network.target`
- Type: `simple`
- User: `firecatcher`
- WorkingDirectory: `/opt/fire_catcher`
- EnvironmentFile: `/opt/fire_catcher/.env`
- ExecStart: `/opt/fire_catcher/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000`
- Restart: `always`
- RestartSec: `5`
- WantedBy: `multi-user.target`

---

## 6. `deploy/nginx.conf`

Nginx server block (not full nginx.conf, just the server block for inclusion).

Requirements:
- Listen on port 80
- `server_name _` (accept any hostname)
- Proxy all requests to `http://127.0.0.1:8000`
- Proxy headers: `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`
- `proxy_read_timeout 60s`
- Static files at `/opt/fire_catcher/static/` served directly by Nginx (location `/static/`)
- Gzip enabled for `text/html text/css application/javascript application/json`
- Access log: `/var/log/nginx/fire_catcher.access.log`
- Error log: `/var/log/nginx/fire_catcher.error.log`

---

## 7. `deploy/deploy.sh`

Bash script for first-time deployment on Ubuntu 22.04 Hetzner server.

Steps in order:
1. `set -e` at top — abort on any error
2. Print each step with `echo "→ step description"`
3. Create system user `firecatcher` if it doesn't exist (no login shell, no home dir)
4. `apt-get install -y python3.11 python3.11-venv nginx`
5. Create `/opt/fire_catcher` and set owner to `firecatcher`
6. Copy project files from current directory to `/opt/fire_catcher` (using `rsync` or `cp -r`)
7. Create virtualenv at `/opt/fire_catcher/venv` and install requirements
8. Create `/opt/fire_catcher/static/` directory (needed for map output)
9. Copy `.env` file if it exists in current dir, otherwise print a warning
10. Copy `deploy/fire_catcher.service` to `/etc/systemd/system/`
11. Copy `deploy/nginx.conf` to `/etc/nginx/sites-available/fire_catcher`
12. Symlink to `/etc/nginx/sites-enabled/fire_catcher` (remove default if present)
13. `systemctl daemon-reload`
14. `systemctl enable --now fire_catcher`
15. `systemctl reload nginx`
16. Print: `✓ Deployed. Visit http://<server-ip>` and remind user to set FIRMS_API_KEY in /opt/fire_catcher/.env

---

## Rules

- Do not modify any `.py` files in the project root
- Do not add dependencies beyond the stack table
- Shell script must be POSIX-compatible bash, no bashisms beyond `[[`
- HTML must be valid and work without a build step
- If something is ambiguous, use the most conservative/safe default and leave a `<!-- TODO: clarify -->` comment in that file
