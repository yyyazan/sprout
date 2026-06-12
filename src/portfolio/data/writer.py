"""Append-only writers for trades.csv and transactions.csv.

Both files use ISO dates (yyyy-mm-dd) and are re-sorted by date after each
append so a manual `tail` shows the newest row last.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from portfolio.data.loader import load_trades, load_transactions


TRADE_COLUMNS = ["ticker", "action", "shares", "date"]
TXN_COLUMNS = ["Date", "Amount (USD)"]


def append_trade(
    path: str | Path,
    *,
    ticker: str,
    action: str,
    shares: float,
    trade_date: date,
) -> None:
    path = Path(path)
    existing = load_trades(path) if path.exists() else pd.DataFrame(columns=TRADE_COLUMNS)
    new_row = pd.DataFrame(
        [{
            "ticker": ticker,
            "action": action,
            "shares": float(shares),
            "date": pd.Timestamp(trade_date),
        }]
    )
    out = pd.concat([existing[TRADE_COLUMNS], new_row], ignore_index=True)
    out = out.sort_values("date", kind="stable").reset_index(drop=True)
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False)


def append_transaction(
    path: str | Path,
    *,
    txn_date: date,
    amount: float,
) -> None:
    """Append one cash flow. `amount` is signed: positive = deposit, negative = withdrawal."""
    path = Path(path)
    existing = load_transactions(path) if path.exists() else pd.DataFrame(columns=TXN_COLUMNS)
    new_row = pd.DataFrame(
        [{
            "Date": pd.Timestamp(txn_date),
            "Amount (USD)": float(amount),
        }]
    )
    out = pd.concat([existing[TXN_COLUMNS], new_row], ignore_index=True)
    out = out.sort_values("Date", kind="stable").reset_index(drop=True)
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False)


# ── SQLite-backed writers (system of record) ────────────────────────────────
# Plain INSERTs — no read-modify-rewrite. SQLite is the writer.


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_trade_db(
    user_id: int,
    conn: sqlite3.Connection,
    *,
    ticker: str,
    action: str,
    shares: float,
    trade_date: date,
    price: float | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO trades (user_id, ticker, action, shares, price, trade_date, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
            ticker.upper(),
            str(action).lower(),
            float(shares),
            float(price) if price is not None else None,
            pd.Timestamp(trade_date).strftime("%Y-%m-%d"),
            _now(),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_transaction_db(
    user_id: int,
    conn: sqlite3.Connection,
    *,
    txn_date: date,
    amount: float,
) -> int:
    """Insert one cash flow. `amount` is signed: + deposit, - withdrawal."""
    cur = conn.execute(
        "INSERT INTO transactions (user_id, txn_date, amount_usd, created_at) "
        "VALUES (?, ?, ?, ?)",
        (
            user_id,
            pd.Timestamp(txn_date).strftime("%Y-%m-%d"),
            float(amount),
            _now(),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)