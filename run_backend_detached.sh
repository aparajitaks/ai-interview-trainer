#!/usr/bin/env bash
# Run the backend detached (nohup-friendly) from the project root.
# Ensures the working directory is the project root, activates venv if present,
# exports PYTHONPATH so 'api' package is importable, and starts uvicorn with logs.

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

# Ensure Python can import local packages
export PYTHONPATH="$ROOT_DIR:${PYTHONPATH-}"

# Start uvicorn in background and redirect output to uvicorn.log
echo "Starting backend from $ROOT_DIR; logs -> $ROOT_DIR/uvicorn.log"
PORT=8000

# if port is already in use, report and exit
if command -v lsof >/dev/null 2>&1; then
  if lsof -iTCP:${PORT} -sTCP:LISTEN -Pn >/dev/null 2>&1; then
    echo "Port ${PORT} already in use; aborting start. Check existing backend process or kill it." >&2
    exit 1
  fi
fi

nohup bash -lc "$PYTHON_BIN -m uvicorn api.main:app --host 127.0.0.1 --port ${PORT}" > "$ROOT_DIR/uvicorn.log" 2>&1 &
echo $!
