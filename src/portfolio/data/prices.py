"""yfinance wrappers with in-memory caching for the process lifetime.

DuckDB-backed disk cache lands in M2.5 — for now, every fresh boot pays the
yfinance cold-call cost once. The store-portfolio pattern in app/main.py
absorbs this at startup so user-facing callbacks stay fast.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache

import pandas as pd
import yfinance as yf

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
    try:
        hist = yf.Ticker(ticker).history(period="max")
    except Exception:
        _HISTORY_CACHE[ticker] = pd.Series(dtype=float)
        return _HISTORY_CACHE[ticker]
    if hist.empty:
        _HISTORY_CACHE[ticker] = pd.Series(dtype=float)
        return _HISTORY_CACHE[ticker]
    hist.index = _strip_tz(hist.index)
    series = hist["Close"]
    _HISTORY_CACHE[ticker] = series
    return series


def histories(tickers: list[str]) -> dict[str, pd.Series]:
    """Bulk-load close-price histories. Empty series for delisted tickers."""
    return {t: history(t) for t in tickers}


def history_from(ticker: str, start: datetime | pd.Timestamp) -> pd.Series:
    """Close-price history starting at `start`. Used for benchmarks (SPY/QQQ)."""
    try:
        hist = yf.Ticker(ticker).history(start=start)
    except Exception:
        return pd.Series(dtype=float)
    if hist.empty:
        return pd.Series(dtype=float)
    hist.index = _strip_tz(hist.index)
    return hist["Close"]


def splits(ticker: str) -> pd.Series:
    if ticker in _SPLITS_CACHE:
        return _SPLITS_CACHE[ticker]
    try:
        s = yf.Ticker(ticker).splits
    except Exception:
        _SPLITS_CACHE[ticker] = pd.Series(dtype=float)
        return _SPLITS_CACHE[ticker]
    if s.empty:
        _SPLITS_CACHE[ticker] = pd.Series(dtype=float)
        return _SPLITS_CACHE[ticker]
    s = s.copy()
    s.index = _strip_tz(s.index)
    _SPLITS_CACHE[ticker] = s
    return s


@lru_cache(maxsize=128)
def spot(ticker: str) -> float | None:
    """Latest live price (fast_info.last_price). LRU-cached per process."""
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
    """Sector + company name from yfinance `.info`. Cached per process.

    `.info` is a heavy network call, so this is warmed once at boot inside the
    snapshot. Returns {} for delisted/unknown tickers (yfinance can raise on
    its internal cache) — callers fall back to neutral suit/name defaults.
    """
    if ticker in _PROFILE_CACHE:
        return _PROFILE_CACHE[ticker]
    try:
        info = yf.Ticker(ticker).info or {}
        prof = {
            "sector": info.get("sector", "") or "",
            "name": info.get("longName") or info.get("shortName") or "",
        }
    except Exception:
        prof = {}
    _PROFILE_CACHE[ticker] = prof
    return prof
