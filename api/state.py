"""Per-user snapshot cache (replaces app/state.py's single global).

Compute-once-then-cache, keyed by user_id. Write endpoints call invalidate()
after a trade/transaction lands so the next read recomputes. One Uvicorn worker
keeps this cache authoritative (see the migration plan's concurrency note).
"""
from __future__ import annotations

from portfolio.data import db as db_mod
from portfolio.pipeline import PortfolioSnapshot, run

from api.config import BENCHMARK_TICKERS

_CACHE: dict[int, PortfolioSnapshot] = {}


def get_snapshot(user_id: int = db_mod.DEFAULT_USER_ID) -> PortfolioSnapshot:
    if user_id not in _CACHE:
        conn = db_mod.connect()
        _CACHE[user_id] = run(user_id, conn=conn, benchmarks=BENCHMARK_TICKERS)
    return _CACHE[user_id]


def invalidate(user_id: int = db_mod.DEFAULT_USER_ID) -> None:
    _CACHE.pop(user_id, None)


def refresh(user_id: int = db_mod.DEFAULT_USER_ID) -> PortfolioSnapshot:
    invalidate(user_id)
    return get_snapshot(user_id)
