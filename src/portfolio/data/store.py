"""DuckDB + Parquet analytical layer and durable price cache.

**DuckDB reads, SQLite writes.** This module owns the shared Parquet price
store (market data, not user data). Price *content* is persisted as Parquet
here; price *freshness* metadata is written to SQLite (`price_cache_meta`) via
:mod:`portfolio.data.db`. DuckDB is used to read Parquet (and, via
:func:`analytics_connection`, to join the SQLite system of record read-only for
future backtesting/ML) — it never writes the system of record.

The cache replaces the old per-process in-memory dicts in ``prices.py`` with a
durable store that survives restarts and is shared across users/workers. A
small TTL per kind keeps it fresh; on a yfinance failure a stale cache is
preferred over an empty result.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from portfolio.data import db as db_mod

_REPO_ROOT = Path(__file__).resolve().parents[3]
PARQUET_DIR = Path(os.environ.get("PORTFOLIO_PRICES", _REPO_ROOT / "data" / "prices"))
_HISTORY_DIR = PARQUET_DIR / "history"
_SPLITS_DIR = PARQUET_DIR / "splits"
_PROFILE_DIR = PARQUET_DIR / "profile"
_DIVIDENDS_DIR = PARQUET_DIR / "dividends"

# Time-to-live per cache kind, in seconds.
TTL = {
    "history": 24 * 3600,      # daily closes — refresh once a day
    "dividends": 24 * 3600,   # dividend payments — refresh once a day
    "splits": 7 * 24 * 3600,   # corporate actions rarely change
    "profile": 30 * 24 * 3600, # sector/name almost never change
}

_meta_conn = None  # lazily-opened SQLite connection for price_cache_meta


def _conn():
    global _meta_conn
    if _meta_conn is None:
        _meta_conn = db_mod.connect()
        db_mod.init_schema(_meta_conn)
    return _meta_conn


def _ensure_dirs() -> None:
    for d in (_HISTORY_DIR, _SPLITS_DIR, _PROFILE_DIR, _DIVIDENDS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _safe(ticker: str) -> str:
    return ticker.replace("/", "_").replace("\\", "_")


def _history_path(ticker: str) -> Path:
    return _HISTORY_DIR / f"{_safe(ticker)}.parquet"


def _splits_path(ticker: str) -> Path:
    return _SPLITS_DIR / f"{_safe(ticker)}.parquet"


def _profile_path(ticker: str) -> Path:
    return _PROFILE_DIR / f"{_safe(ticker)}.json"


def is_fresh(ticker: str, kind: str) -> bool:
    """True if a cache entry exists and is younger than its TTL."""
    row = db_mod.get_cache_meta(_conn(), ticker, kind)
    if row is None:
        return False
    try:
        ts = datetime.fromisoformat(row["last_fetched"])
    except (ValueError, TypeError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    return age < TTL.get(kind, 0)


# ── series (history / splits) as Parquet, read via DuckDB ───────────────────


def _read_series(path: Path) -> pd.Series | None:
    if not path.exists():
        return None
    df = duckdb.execute(
        "SELECT idx, val FROM read_parquet(?) ORDER BY idx", [str(path)]
    ).df()
    if df.empty:
        return pd.Series(dtype=float)
    return pd.Series(df["val"].to_numpy(), index=pd.DatetimeIndex(df["idx"]))


def _write_series(path: Path, series: pd.Series, ticker: str, kind: str) -> None:
    _ensure_dirs()
    df = pd.DataFrame(
        {"idx": pd.DatetimeIndex(series.index), "val": series.to_numpy()}
    )
    df.to_parquet(path, index=False)
    db_mod.upsert_cache_meta(_conn(), ticker, kind, len(series))


def read_history(ticker: str) -> pd.Series | None:
    return _read_series(_history_path(ticker))


def write_history(ticker: str, series: pd.Series) -> None:
    _write_series(_history_path(ticker), series, ticker, "history")


def read_splits(ticker: str) -> pd.Series | None:
    return _read_series(_splits_path(ticker))


def write_splits(ticker: str, series: pd.Series) -> None:
    _write_series(_splits_path(ticker), series, ticker, "splits")


def _dividends_path(ticker: str) -> Path:
    return _DIVIDENDS_DIR / f"{_safe(ticker)}.parquet"


def read_dividends(ticker: str) -> pd.Series | None:
    return _read_series(_dividends_path(ticker))


def write_dividends(ticker: str, series: pd.Series) -> None:
    _write_series(_dividends_path(ticker), series, ticker, "dividends")


# ── profile (dict) as JSON ──────────────────────────────────────────────────


def read_profile(ticker: str) -> dict | None:
    path = _profile_path(ticker)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def write_profile(ticker: str, prof: dict) -> None:
    _ensure_dirs()
    _profile_path(ticker).write_text(json.dumps(prof))
    db_mod.upsert_cache_meta(_conn(), ticker, "profile", len(prof))


# ── analytical engine (for future backtesting / ML) ─────────────────────────


def analytics_connection() -> duckdb.DuckDBPyConnection:
    """A DuckDB connection with the SQLite system of record attached read-only.

    Lets analytical queries join user trades against the Parquet price history
    without ever writing through DuckDB. Example:

        con = analytics_connection()
        con.sql("SELECT * FROM sor.trades t JOIN read_parquet(...) p ...")
    """
    con = duckdb.connect()
    con.execute("INSTALL sqlite; LOAD sqlite")
    con.execute(f"ATTACH '{db_mod.DEFAULT_DB_PATH}' AS sor (TYPE sqlite, READ_ONLY)")
    return con
