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

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pandas as pd
import yfinance as yf

from portfolio.data import store

# Concurrent yfinance fetches share one worker cap — stay under Yahoo's
# throttling radar while still collapsing N round-trips into ~1.
_MAX_QUOTE_WORKERS = 8

# L1 in-process memo (cleared on process restart).
_HISTORY_CACHE: dict[str, pd.Series] = {}
_SPLITS_CACHE: dict[str, pd.Series] = {}
_PROFILE_CACHE: dict[str, dict] = {}
_DIVIDENDS_CACHE: dict[str, pd.Series] = {}


# Ticker renames: a holding keeps its original symbol everywhere (trades, display, and
# the cache key), but the live yfinance feed has moved to a new symbol. We fetch the new
# symbol yet cache it under the original, so the price history stays continuous across the
# rename (the new symbol carries the full back-history, so values don't jump).
_YF_RENAMES = {
    "VSCO": "VSXY",   # Victoria's Secret — ticker change, 2026-06
}


def yf_symbol(ticker: str) -> str:
    """Map a position ticker to the symbol yfinance currently serves it under."""
    return _YF_RENAMES.get(ticker.upper(), ticker)


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
        hist = yf.Ticker(yf_symbol(ticker)).history(period="max")
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


def _parallel(fn, keys: list[str]) -> dict:
    """Fan a per-ticker fetch out over threads, preserving key order.

    Safe with the cache stack: L1 dict writes are GIL-atomic, Parquet paths are
    per-ticker, and the shared sqlite meta connection is serialized by CPython.
    """
    if len(keys) <= 1:
        return {k: fn(k) for k in keys}
    with ThreadPoolExecutor(max_workers=min(_MAX_QUOTE_WORKERS, len(keys))) as pool:
        return dict(zip(keys, pool.map(fn, keys)))


def histories(tickers: list[str]) -> dict[str, pd.Series]:
    """Bulk-load close-price histories. Empty series for delisted tickers."""
    return _parallel(history, list(tickers))


def splits_map(tickers: list[str]) -> dict[str, pd.Series]:
    """Bulk-load split series, misses fetched concurrently."""
    return _parallel(splits, list(tickers))


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
        s = yf.Ticker(yf_symbol(ticker)).splits
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


def dividends(ticker: str) -> pd.Series:
    """Per-share dividend payment history (split-adjusted). Durably cached.

    Empty series for non-payers / delisted tickers. Used for the trailing
    12-month dividend rate when a forward rate isn't on the profile.
    """
    if ticker in _DIVIDENDS_CACHE:
        return _DIVIDENDS_CACHE[ticker]

    cached = store.read_dividends(ticker)
    if cached is not None and not cached.empty and store.is_fresh(ticker, "dividends"):
        _DIVIDENDS_CACHE[ticker] = cached
        return cached

    try:
        d = yf.Ticker(yf_symbol(ticker)).dividends
    except Exception:
        d = None
    if d is None or d.empty:
        result = cached if (cached is not None and not cached.empty) else pd.Series(dtype=float)
        _DIVIDENDS_CACHE[ticker] = result
        return result

    d = d.copy()
    d.index = _strip_tz(d.index)
    store.write_dividends(ticker, d)
    _DIVIDENDS_CACHE[ticker] = d
    return d


# Live quotes: short-TTL in-process cache + threaded fan-out. fast_info is one
# HTTP round-trip per ticker no matter the wrapper (yf.Tickers included), so a
# thread pool is the real batching. Spot is inherently live — never persisted.
_QUOTE_TTL = 30.0
_quote_cache: dict[str, tuple[float, dict]] = {}  # ticker -> (fetched_at, quote)


def _fetch_quote(ticker: str) -> dict:
    # yf.Ticker is constructed per task — instances aren't thread-safe.
    price = prev = None
    try:
        fi = yf.Ticker(yf_symbol(ticker)).fast_info
        price = float(fi.last_price)
        prev = float(fi.previous_close)
    except Exception:
        pass
    return {"price": price, "prev_close": prev}


def quotes(tickers: list[str], *, max_age: float = _QUOTE_TTL) -> dict[str, dict]:
    """Live quotes ({price, prev_close}) for many tickers, misses fetched
    concurrently in one threaded fan-out.

    Entries younger than `max_age` seconds are served from cache; pass 0.0 to
    force fresh quotes. A failed fetch yields None values (same posture as the
    old per-ticker spot()).
    """
    now = time.time()
    out: dict[str, dict] = {}
    misses: list[str] = []
    for t in tickers:
        hit = _quote_cache.get(t)
        if hit is not None and now - hit[0] < max_age:
            out[t] = hit[1]
        else:
            misses.append(t)
    if misses:
        with ThreadPoolExecutor(max_workers=min(_MAX_QUOTE_WORKERS, len(misses))) as pool:
            for t, q in zip(misses, pool.map(_fetch_quote, misses)):
                _quote_cache[t] = (now, q)
                out[t] = q
    return out


def spot(ticker: str) -> float | None:
    """Latest live price (fast_info.last_price), via the shared quote cache."""
    return quotes([ticker])[ticker]["price"]


def price_on_date(ticker: str, date: pd.Timestamp) -> float | None:
    """Split-adjusted close on the nearest trading day on or before `date`."""
    series = history(ticker)
    if series.empty:
        return None
    valid = series[series.index <= date]
    return float(valid.iloc[-1]) if not valid.empty else None


def adjusted_trade_price(
    ticker: str,
    date: pd.Timestamp,
    recorded: float | None = None,
    split_factor: float = 1.0,
) -> float | None:
    """Per-share trade price in today's split-adjusted terms.

    Prefers the *recorded execution price* (what was actually paid/received),
    divided forward by any post-trade splits so it lines up with `adj_shares`
    and live spot. Falls back to the back-adjusted yfinance close on the trade
    date when no price was recorded (older trades / the price-less CSV path).
    Works for buys and sells alike — pair it with `adj_shares`, whose sign
    already encodes the direction.
    """
    if recorded is not None and not pd.isna(recorded):
        return float(recorded) / split_factor
    return price_on_date(ticker, date)


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
        info = yf.Ticker(yf_symbol(ticker)).info or {}
        prof = {
            "sector": info.get("sector", "") or "",
            "name": info.get("longName") or info.get("shortName") or "",
            # forward annual dividend per share ($); None for non-payers. Free to
            # grab from the .info we already fetch -> the dividends calc prefers it.
            "dividend_rate": info.get("dividendRate"),
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
