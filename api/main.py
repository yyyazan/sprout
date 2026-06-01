"""FastAPI app — serves the portfolio analytics as JSON to the SvelteKit frontend.

Run from the repo root:

    PYTHONPATH=src .venv/bin/uvicorn api.main:app --reload --port 8000

One worker only (the per-user snapshot cache in api.state is in-process).
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api import backup, state
from api.config import CORS_ORIGINS
from api.routers import dashboard, entries

# Static SvelteKit bundle (adapter-static). Served by this same process so the
# whole app is one deploy; missing in dev when the frontend runs on Vite :5173.
BUILD_DIR = (Path(__file__).resolve().parent.parent / "web" / "build")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the default user's snapshot at boot (hits yfinance / Parquet cache).
    try:
        state.get_snapshot()
    except Exception:
        pass  # boot even if data is missing; first request will retry

    # Daily off-site backup to R2 — only if the R2_* env vars are configured.
    backup_task = None
    if backup.is_configured():
        backup_task = asyncio.create_task(backup.run_backup_loop())
    else:
        logging.getLogger("sprout.backup").info("R2 not configured; backups disabled")

    yield

    if backup_task:
        backup_task.cancel()


app = FastAPI(title="Sprout API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(entries.router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# Frontend: serve real files from build/, fall back to index.html for client
# routes (e.g. /investments/AAPL). Registered last so /api and /healthz win.
if BUILD_DIR.is_dir():

    @app.get("/{path:path}")
    def spa(path: str):
        candidate = (BUILD_DIR / path).resolve()
        if path and candidate.is_relative_to(BUILD_DIR) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(BUILD_DIR / "index.html")
else:

    @app.get("/")
    def no_build():
        raise HTTPException(
            503,
            "Frontend not built. Run `npm run build` in web/, or use Vite dev on :5173.",
        )
