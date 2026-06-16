#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  echo ".venv not found. Run ./setup.command first."
  exit 1
fi

if [ ! -f "frontend/dist/index.html" ]; then
  echo "frontend/dist not found. Building dashboard..."
  cd frontend
  npm run build
  cd "$ROOT_DIR"
fi

PORT="${PORT:-8010}"
HOST="${HOST:-127.0.0.1}"

echo "Starting Network Service Dependency Analyzer"
echo "URL: http://${HOST}:${PORT}/"
echo

exec .venv/bin/uvicorn backend.main:app --host "$HOST" --port "$PORT"
