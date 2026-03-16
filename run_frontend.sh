#!/usr/bin/env bash
set -euo pipefail

# Start frontend dev server and expose to localhost
cd "$(dirname "$0")/frontend" || exit 1

npm run dev -- --host
