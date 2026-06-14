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
source "$VENV_DIR/bin/activate"

exec uvicorn main:app --reload --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" "$@"
