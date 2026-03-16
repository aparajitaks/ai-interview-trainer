#!/usr/bin/env bash
# Development helper to run the backend with hot reload.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Activate venv if present
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

python -m uvicorn api.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
