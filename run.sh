#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "Virtual environment not found at: $VENV_DIR" >&2
  echo "Create it first with: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

cd "$APP_DIR"

if [[ -z "${FIRMS_API_KEY:-}" && -f "$APP_DIR/.env" ]]; then
  FIRMS_API_KEY="$(awk -F= '/^FIRMS_API_KEY=/ {print $2; exit}' "$APP_DIR/.env")"
fi

if [[ -z "${FIRMS_API_KEY:-}" ]]; then
  echo "FIRMS_API_KEY is required before starting Sentinela Verde." >&2
  echo "Create .env from .env.example and set FIRMS_API_KEY to your NASA FIRMS map key." >&2
  echo "Example: cp .env.example .env" >&2
  exit 1
fi

source "$VENV_DIR/bin/activate"

exec uvicorn sentinela_verde.main:app --reload --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" "$@"
