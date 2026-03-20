#!/usr/bin/env bash
# Development helper to run the backend with hot reload.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Prefer project-local virtualenv Python if available
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi

if [ -f .env ]; then
  # shellcheck disable=SC1091
  source .env
fi

export TRANSFORMERS_OFFLINE=${TRANSFORMERS_OFFLINE:-1}

"$PYTHON_BIN" -m uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8000
