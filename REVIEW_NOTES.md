# Review Notes — Claude

*2026-06-04 — first review pass*

---

## Verdict by file

| File | Agent | Grade | Status |
|---|---|---|---|
| `config.py` | Gemini | A | Verbatim spec match. No changes needed. |
| `db.py` | Codex | A | Clean, correct, well-structured. No changes needed. |
| `fetcher.py` | Codex | A | Solid error handling, good CSV validation. No changes needed. |
| `map_renderer.py` | Codex | A- | Works correctly. Minor undocumented behavior (see below). |
| `main.py` | Codex | B+ | One scalability issue (see below). |
| `test_db.py` | Codex | A | All 5 required cases covered. Backdating trick is clean. |
| `test_fetcher.py` | Codex | A | All 3 cases covered. Monkeypatch approach is correct. |
| `templates/index.html` | Gemini | A | Meets all spec requirements. Cache-busting on iframe reload is smarter than spec asked for. |
| `deploy/nginx.conf` | Gemini | A | All directives correct. |
| `deploy/fire_catcher.service` | Gemini | A | Correct. |
| `deploy/deploy.sh` | Gemini | B | One cosmetic bug (see below). |
| `requirements.txt` | Gemini | A- | `pytest`/`pytest-asyncio` left unpinned. Acceptable for MVP. |

---

## Issues requiring fixes

### [FIX REQUIRED] `deploy/deploy.sh` — echo messages are malformed

**Agent**: Gemini  
**Severity**: Cosmetic but embarrassing in production output

Gemini took the prompt's format hint literally. Every echo says `"→ step description: ..."` instead of a real description.

**Lines affected**: 4, 9, 13, 17, 21, 27, 30, 37, 42, 48

Replace each echo with a meaningful message. For example:
```bash
# Wrong (what Gemini wrote):
echo "→ step description: Creating system user firecatcher"

# Correct:
echo "→ Creating system user 'firecatcher'"
```

Full corrected messages:
```
→ Creating system user 'firecatcher'
→ Installing system dependencies (python3.11, nginx, rsync)
→ Setting up /opt/fire_catcher directory
→ Copying project files
→ Creating virtualenv and installing requirements
→ Creating static output directory
→ Copying .env file
→ Installing systemd service
→ Configuring Nginx
→ Starting services
```

---

### [MINOR] `main.py:103` — `total_events` loads entire table into memory

**Agent**: Codex  
**Severity**: Non-blocking for MVP, will degrade at scale

```python
# Current (loads all rows, then counts in Python):
"total_events": len(get_all_events(DB_FILE_PATH)),
```

**Recommended fix**: add a `count_events(db_path)` function to `db.py` that runs `SELECT COUNT(*) FROM fire_events` and use it here.

Not blocking MVP — fine to defer unless the DB grows large.

---

### [INFO] `map_renderer.py:59` — undocumented zoom behavior

**Agent**: Codex  
**Severity**: No action needed, documenting for awareness

When events are present, zoom is hardcoded to `6` instead of `DEFAULT_ZOOM` (4). This is actually better UX for a regional dataset. No fix needed — noting it so future agents don't revert it thinking it's a bug.

---

## What both agents did well

**Codex**:
- Correct `asyncio.run()` usage inside the APScheduler background thread (no event loop conflict)
- `INSERT OR IGNORE` with per-row `rowcount` check is the right pattern for counting new inserts
- `StaticFiles(check_dir=False)` avoids a startup crash when `static/` doesn't exist yet
- `max_instances=1, coalesce=True` on the scheduler job prevents overlapping fetches

**Gemini**:
- Cache-busting query param on iframe reload (`?t=<timestamp>`) is better than the spec's `src += ''`
- Disabled button state during fetch prevents double-submit
- `rsync --exclude venv --exclude .git` is the right way to deploy

---

## Next step

Fix `deploy.sh` echo messages (Gemini task). Everything else is ready to run.  
To test locally: create a `.env` with `FIRMS_API_KEY=yourkey` and run `uvicorn main:app --reload`.
