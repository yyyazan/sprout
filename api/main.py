"""FastAPI app — serves the portfolio analytics as JSON to the SvelteKit frontend.

Run from the repo root:

    PYTHONPATH=src .venv/bin/uvicorn api.main:app --reload --port 8000

One worker only (the per-user snapshot cache in api.state is in-process).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import state
from api.config import CORS_ORIGINS
from api.routers import dashboard, entries


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the default user's snapshot at boot (hits yfinance / Parquet cache).
    try:
        state.get_snapshot()
    except Exception:
        pass  # boot even if data is missing; first request will retry
    yield


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
