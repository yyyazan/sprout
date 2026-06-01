#!/usr/bin/env bash
# Local dev: start FastAPI (:8000) + Vite (:5173) together, open http://localhost:5173.
# Vite proxies /api -> :8000, so the frontend's relative /api calls just work.
# Ctrl-C stops both. Run from the repo root: ./dev.sh
set -euo pipefail
cd "$(dirname "$0")"

# Kill both child processes when this script exits (Ctrl-C, error, or normal quit).
trap "kill 0" EXIT

echo "→ FastAPI  http://localhost:8000  (api)"
# `python -m uvicorn` (not .venv/bin/uvicorn) so it survives folder renames —
# venv console scripts hardcode an absolute shebang that breaks if the dir moves.
PYTHONPATH=src .venv/bin/python -m uvicorn api.main:app --reload --port 8000 &

echo "→ Vite     http://localhost:5173  (open this one)"
cd web && npm run dev
