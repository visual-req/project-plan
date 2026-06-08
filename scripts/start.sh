#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Env vars (optional):"
echo "  export HOST=0.0.0.0"
echo "  export PORT=8014"
echo "  export CONFIG=\"$ROOT_DIR/backend/config.yaml\""
echo "  export LLM_API_KEY=\"YOUR_API_KEY\""
echo "Defaults: HOST=0.0.0.0 PORT=8010 CONFIG=$ROOT_DIR/backend/config.yaml"
echo ""
PORT="${PORT:-8010}"
echo "Starting backend..."
echo "Frontend is served by backend static hosting."
echo "Open: http://localhost:${PORT}/"
echo ""
exec "$ROOT_DIR/scripts/start_backend.sh"
