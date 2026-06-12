"""SQLite system of record — connection, schema, and a thin data-access layer.

This is the lowest layer of the data stack: it owns the SQLite file and the
only place user data is *written*. Analytics never import this directly — the
loader/writer seams (``loader.load_trades_db`` etc.) sit on top and hand
DataFrames to the pipeline exactly as the old CSV path did.

Boundary rule for the wider stack: **SQLite writes, DuckDB reads.** The only
writers are user trades/transactions/reconciliation here and the price-cache
metadata in :mod:`portfolio.data.store`.

All tables carry a ``user_id`` so a friend can be added later with no schema
change. Until real auth lands, everything uses the seeded default user
(``user_id = 1``).
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Repo root = three levels up from this file (src/portfolio/data/db.py).
_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = Path(os.environ.get("PORTFOLIO_DB", _REPO_ROOT / "data" / "portfolio.db"))

DEFAULT_USER_ID = 1
# Untraced cash drift seeded for the default user (FX rounding + legacy fees).
# Lifted out of analytics/cash.py so it becomes per-user data. Last reconciled
# 2026-05-28, broker cash = $3.
DEFAULT_RECONCILIATION_OFFSET = -107.0

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    email        TEXT UNIQUE,
    display_name TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(user_id),
    ticker     TEXT    NOT NULL,
    action     TEXT    NOT NULL CHECK (action IN ('buy', 'sell')),
    shares     REAL    NOT NULL,
    price      REAL,
    trade_date TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(user_id, trade_date);

CREATE TABLE IF NOT EXISTS transactions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(user_id),
    txn_date   TEXT    NOT NULL,
    amount_usd REAL    NOT NULL,
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_txn_user ON transactions(user_id, txn_date);

CREATE TABLE IF NOT EXISTS cash_reconciliation (
    user_id       INTEGER PRIMARY KEY REFERENCES users(user_id),
    offset_usd    REAL NOT NULL DEFAULT 0.0,
    reconciled_at TEXT,
    note          TEXT
);

-- Non-held tickers the user wants on the radar (the "+ Watch" button).
CREATE TABLE IF NOT EXISTS watchlist (
    user_id  INTEGER NOT NULL REFERENCES users(user_id),
    ticker   TEXT    NOT NULL,
    added_at TEXT    NOT NULL,
    PRIMARY KEY (user_id, ticker)
);

-- Shared market-data cache freshness (the Parquet files hold the data itself).
CREATE TABLE IF NOT EXISTS price_cache_meta (
    ticker       TEXT NOT NULL,
    kind         TEXT NOT NULL CHECK (kind IN ('history', 'splits', 'profile', 'spot', 'dividends')),
    last_fetched TEXT NOT NULL,
    rows         INTEGER,
    PRIMARY KEY (ticker, kind)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection tuned for a small multi-user app.

    WAL mode + a busy timeout keep the occasional concurrent write safe. Open a
    fresh connection per request/thread — never share one across threads.
    """
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI runs sync endpoints on a threadpool, and
    # store.py keeps one long-lived metadata connection that any request thread
    # may touch (e.g. caching a brand-new ticker's profile). CPython's sqlite3
    # is built threadsafe (sqlite3.threadsafety == 3), which serializes access.
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate_price_cache_meta(conn: sqlite3.Connection) -> None:
    """Widen the price_cache_meta `kind` CHECK as new cache kinds are added.

    CREATE TABLE IF NOT EXISTS can't alter an existing CHECK, so rebuild the table
    when its stored definition predates a kind. Cache-freshness metadata only
    (the Parquet files hold the data), so the rebuild just copies the rows.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='price_cache_meta'"
    ).fetchone()
    if row is None or "'dividends'" in (row["sql"] or ""):
        return
    conn.executescript(
        """
        ALTER TABLE price_cache_meta RENAME TO _pcm_old;
        CREATE TABLE price_cache_meta (
            ticker       TEXT NOT NULL,
            kind         TEXT NOT NULL CHECK (kind IN ('history', 'splits', 'profile', 'spot', 'dividends')),
            last_fetched TEXT NOT NULL,
            rows         INTEGER,
            PRIMARY KEY (ticker, kind)
        );
        INSERT INTO price_cache_meta (ticker, kind, last_fetched, rows)
            SELECT ticker, kind, last_fetched, rows FROM _pcm_old;
        DROP TABLE _pcm_old;
        """
    )


def _migrate_trades_price(conn: sqlite3.Connection) -> None:
    """Add the per-share execution price to trades created before it existed.

    NULL means "unknown" — rows are backfilled with the closing price by
    scripts/backfill_trade_prices.py, and new trades default to the close
    server-side when the user leaves the price blank.
    """
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(trades)").fetchall()}
    if cols and "price" not in cols:
        conn.execute("ALTER TABLE trades ADD COLUMN price REAL")


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    _migrate_price_cache_meta(conn)
    _migrate_trades_price(conn)
    conn.commit()


def seed_defaults(conn: sqlite3.Connection) -> None:
    """Idempotently create the default user + its reconciliation offset."""
    cur = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (DEFAULT_USER_ID,))
    if cur.fetchone() is None:
        conn.execute(
            "INSERT INTO users (user_id, email, display_name, created_at) VALUES (?, NULL, ?, ?)",
            (DEFAULT_USER_ID, "default", _now()),
        )
    cur = conn.execute(
        "SELECT 1 FROM cash_reconciliation WHERE user_id = ?", (DEFAULT_USER_ID,)
    )
    if cur.fetchone() is None:
        conn.execute(
            "INSERT INTO cash_reconciliation (user_id, offset_usd, reconciled_at, note) "
            "VALUES (?, ?, ?, ?)",
            (DEFAULT_USER_ID, DEFAULT_RECONCILIATION_OFFSET, "2026-05-28", "broker cash = $3"),
        )
    conn.commit()


def reconciliation_offset(conn: sqlite3.Connection, user_id: int = DEFAULT_USER_ID) -> float:
    """Per-user cash reconciliation offset (0.0 if none set)."""
    cur = conn.execute(
        "SELECT offset_usd FROM cash_reconciliation WHERE user_id = ?", (user_id,)
    )
    row = cur.fetchone()
    return float(row["offset_usd"]) if row is not None else 0.0


# ── watchlist ────────────────────────────────────────────────────────────────


def watchlist_tickers(conn: sqlite3.Connection, user_id: int = DEFAULT_USER_ID) -> list[str]:
    cur = conn.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at", (user_id,)
    )
    return [r["ticker"] for r in cur.fetchall()]


def watchlist_add(conn: sqlite3.Connection, ticker: str, user_id: int = DEFAULT_USER_ID) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO watchlist (user_id, ticker, added_at) VALUES (?, ?, ?)",
        (user_id, ticker, _now()),
    )
    conn.commit()


def watchlist_remove(conn: sqlite3.Connection, ticker: str, user_id: int = DEFAULT_USER_ID) -> None:
    conn.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
    )
    conn.commit()


# ── price-cache metadata (used by store.py) ─────────────────────────────────


def get_cache_meta(conn: sqlite3.Connection, ticker: str, kind: str) -> sqlite3.Row | None:
    cur = conn.execute(
        "SELECT ticker, kind, last_fetched, rows FROM price_cache_meta "
        "WHERE ticker = ? AND kind = ?",
        (ticker, kind),
    )
    return cur.fetchone()


def upsert_cache_meta(
    conn: sqlite3.Connection, ticker: str, kind: str, rows: int
) -> None:
    conn.execute(
        "INSERT INTO price_cache_meta (ticker, kind, last_fetched, rows) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(ticker, kind) DO UPDATE SET last_fetched = excluded.last_fetched, "
        "rows = excluded.rows",
        (ticker, kind, _now(), rows),
    )
    conn.commit()
