#!/usr/bin/env bash
# Development helper to run the backend with hot reload.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Prefer .venv python when present; allow enabling reload via AIIT_RELOAD=1
PYTHON="python"
if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
fi

# Activate venv for interactive shells if requested
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate || true
fi

RELOAD_FLAG=""
if [ "${AIIT_RELOAD-}" = "1" ] || [ "${AIIT_RELOAD-}" = "true" ]; then
  RELOAD_FLAG="--reload"
fi

"${PYTHON}" -m uvicorn api.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  ${RELOAD_FLAG}
