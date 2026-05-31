#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PORT="${PORT:-8010}"
HOST="${HOST:-0.0.0.0}"
CONFIG="${CONFIG:-$ROOT_DIR/backend/config.yaml}"

PY="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$PY" ]]; then
  python3 -m venv "$ROOT_DIR/.venv"
  "$ROOT_DIR/.venv/bin/python" -m pip install -r "$ROOT_DIR/backend/requirements.txt"
fi

exec "$PY" -m backend.serve --host "$HOST" --port "$PORT" --config "$CONFIG"
