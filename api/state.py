"""Per-user snapshot cache (replaces app/state.py's single global).

Compute-on-read, keyed by user_id, with a short TTL so live prices stay fresh:
a cached snapshot older than SNAPSHOT_TTL_SECONDS is recomputed on the next
read (lazy — no work while nobody's looking at the page). Write endpoints also
call invalidate() so a new trade/transaction shows up immediately. One Uvicorn
worker keeps this cache authoritative (see the migration plan's concurrency note).
"""
from __future__ import annotations

import time

from portfolio.data import db as db_mod
from portfolio.pipeline import PortfolioSnapshot, run

from api.config import BENCHMARK_TICKERS

# Recompute when the cached snapshot is older than this. yfinance histories are
# themselves Parquet-cached (24h TTL), so a refresh is mostly live spot quotes +
# analytics — cheap enough to run at most once a minute for a personal app.
SNAPSHOT_TTL_SECONDS = 60.0

# user_id -> (computed_at_monotonic, snapshot)
_CACHE: dict[int, tuple[float, PortfolioSnapshot]] = {}


def get_snapshot(user_id: int = db_mod.DEFAULT_USER_ID) -> PortfolioSnapshot:
    hit = _CACHE.get(user_id)
    if hit is not None and (time.monotonic() - hit[0]) < SNAPSHOT_TTL_SECONDS:
        return hit[1]
    conn = db_mod.connect()
    snap = run(user_id, conn=conn, benchmarks=BENCHMARK_TICKERS)
    _CACHE[user_id] = (time.monotonic(), snap)
    return snap


def invalidate(user_id: int = db_mod.DEFAULT_USER_ID) -> None:
    _CACHE.pop(user_id, None)


def refresh(user_id: int = db_mod.DEFAULT_USER_ID) -> PortfolioSnapshot:
    invalidate(user_id)
    return get_snapshot(user_id)
