#!/usr/bin/env bash
# Run the backend detached (nohup-friendly) from the project root.
# Ensures the working directory is the project root, activates venv if present,
# exports PYTHONPATH so 'api' package is importable, and starts uvicorn with logs.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Activate virtualenv if available
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
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

nohup bash -lc "python3 -m uvicorn api.main:app --host 127.0.0.1 --port ${PORT}" > "$ROOT_DIR/uvicorn.log" 2>&1 &
echo $!
