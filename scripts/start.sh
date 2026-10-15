#!/usr/bin/env bash
# One-command start for local use.
#   ./scripts/start.sh          -> installs everything, builds the web page, runs the app
#                                  at http://localhost:8000
#   PORT=9000 ./scripts/start.sh -> use another port
# Needs: Python 3.12+ and Node 20+. No database server needed (uses a local SQLite file).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8000}"
PYTHON="${PYTHON:-python3}"

echo "==> Backend: Python environment"
cd "$ROOT/backend"
if [ ! -d venv ]; then
  "$PYTHON" -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install --quiet --disable-pip-version-check -r requirements.txt

if [ ! -f .env ]; then
  cp "$ROOT/.env.example" .env
  echo "    created backend/.env from .env.example"
fi

echo "==> Frontend: install and build"
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm ci --no-audit --no-fund
fi
if [ ! -f dist/index.html ] || [ -n "$(find src index.html package.json -newer dist/index.html -print -quit)" ]; then
  npm run build
fi

echo "==> Starting the app on http://localhost:${PORT}  (Ctrl+C to stop)"
cd "$ROOT/backend"
# The app creates/updates the database tables and loads the questions by itself on start-up.
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
