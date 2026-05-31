"""yfinance wrappers backed by a durable DuckDB/Parquet cache.

Public signatures are unchanged from the old in-memory version — analytics
import these by name (e.g. ``cash.py``), so behaviour is drop-in. What changed
is the cache layer: history/splits/profile now persist to a shared Parquet
store (:mod:`portfolio.data.store`) with per-kind TTL freshness, instead of
process-lifetime dicts. This survives restarts, is shared across users/workers,
and makes the benchmark series deterministic (the old uncached ``history_from``
jittered with the live close).

Two cache tiers: an in-process memo (L1, fast within a run) over the Parquet
store (L2, durable). On a yfinance failure a stale L2 entry is preferred over
an empty result; only genuine "no data anywhere" yields an empty series, and
empty results are never written to Parquet (so delisted tickers can't poison
the cache).
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache

import pandas as pd
import yfinance as yf

from portfolio.data import store

# L1 in-process memo (cleared on process restart).
_HISTORY_CACHE: dict[str, pd.Series] = {}
_SPLITS_CACHE: dict[str, pd.Series] = {}
_PROFILE_CACHE: dict[str, dict] = {}


def _strip_tz(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return idx.tz_localize(None) if idx.tz is not None else idx


def history(ticker: str) -> pd.Series:
    """Full split-adjusted close-price history for a single ticker.

    Returns an empty series for delisted/unknown tickers — yfinance can raise
    AttributeError on its internal cache for those cases.
    """
    if ticker in _HISTORY_CACHE:
        return _HISTORY_CACHE[ticker]

    cached = store.read_history(ticker)
    if cached is not None and not cached.empty and store.is_fresh(ticker, "history"):
        _HISTORY_CACHE[ticker] = cached
        return cached

    try:
        hist = yf.Ticker(ticker).history(period="max")
    except Exception:
        hist = None
    if hist is None or hist.empty:
        # Fall back to a stale cache before giving up.
        result = cached if (cached is not None and not cached.empty) else pd.Series(dtype=float)
        _HISTORY_CACHE[ticker] = result
        return result

    hist.index = _strip_tz(hist.index)
    series = hist["Close"]
    store.write_history(ticker, series)
    _HISTORY_CACHE[ticker] = series
    return series


def histories(tickers: list[str]) -> dict[str, pd.Series]:
    """Bulk-load close-price histories. Empty series for delisted tickers."""
    return {t: history(t) for t in tickers}


def history_from(ticker: str, start: datetime | pd.Timestamp) -> pd.Series:
    """Close-price history starting at `start`. Used for benchmarks (SPY/QQQ).

    Derived from the cached full ``history`` (sliced to ``>= start``) so it is
    durable and deterministic rather than a fresh, jittering yfinance call.
    """
    series = history(ticker)
    if series.empty:
        return series
    return series[series.index >= pd.Timestamp(start)]


def splits(ticker: str) -> pd.Series:
    if ticker in _SPLITS_CACHE:
        return _SPLITS_CACHE[ticker]

    cached = store.read_splits(ticker)
    if cached is not None and store.is_fresh(ticker, "splits"):
        _SPLITS_CACHE[ticker] = cached
        return cached

    try:
        s = yf.Ticker(ticker).splits
    except Exception:
        s = None
    if s is None or s.empty:
        result = cached if cached is not None else pd.Series(dtype=float)
        _SPLITS_CACHE[ticker] = result
        return result

    s = s.copy()
    s.index = _strip_tz(s.index)
    store.write_splits(ticker, s)
    _SPLITS_CACHE[ticker] = s
    return s


@lru_cache(maxsize=128)
def spot(ticker: str) -> float | None:
    """Latest live price (fast_info.last_price). LRU-cached per process.

    Spot is inherently live, so it stays an in-process cache only (not persisted).
    """
    try:
        return float(yf.Ticker(ticker).fast_info.last_price)
    except Exception:
        return None


def price_on_date(ticker: str, date: pd.Timestamp) -> float | None:
    """Split-adjusted close on the nearest trading day on or before `date`."""
    series = history(ticker)
    if series.empty:
        return None
    valid = series[series.index <= date]
    return float(valid.iloc[-1]) if not valid.empty else None


def profile(ticker: str) -> dict:
    """Sector + company name from yfinance `.info`. Durably cached.

    `.info` is a heavy network call, so this is warmed once at boot inside the
    snapshot. Returns {} for delisted/unknown tickers (yfinance can raise on
    its internal cache) — callers fall back to neutral suit/name defaults.
    """
    if ticker in _PROFILE_CACHE:
        return _PROFILE_CACHE[ticker]

    cached = store.read_profile(ticker)
    if cached is not None and store.is_fresh(ticker, "profile"):
        _PROFILE_CACHE[ticker] = cached
        return cached

    try:
        info = yf.Ticker(ticker).info or {}
        prof = {
            "sector": info.get("sector", "") or "",
            "name": info.get("longName") or info.get("shortName") or "",
        }
    except Exception:
        prof = None
    if prof is None:
        result = cached if cached is not None else {}
        _PROFILE_CACHE[ticker] = result
        return result

    store.write_profile(ticker, prof)
    _PROFILE_CACHE[ticker] = prof
    return prof
