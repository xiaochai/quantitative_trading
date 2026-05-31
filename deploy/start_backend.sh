#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
ENV_FILE="$PROJECT_ROOT/deploy/.env"

if [[ -f "$ENV_FILE" ]]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

export PYTHONUNBUFFERED=1

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8001}"

cd "$BACKEND_DIR"
exec "$PROJECT_ROOT/venv/bin/uvicorn" api.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
