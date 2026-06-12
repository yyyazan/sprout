"""Load trades.csv and transactions.csv into normalized DataFrames.

trades.csv schema:        ticker, action, shares, date
transactions.csv schema:  Date, Amount (USD)

Both files use ISO dates (yyyy-mm-dd). A transaction's direction is inferred
from the sign of Amount (USD): positive = deposit, negative = withdrawal.
Broker-drift reconciliation lives in code (cash.CASH_RECONCILIATION_OFFSET),
never as fudge rows here.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def _normalize_trades(df: pd.DataFrame) -> pd.DataFrame:
    """Shared normalization so the CSV and DB paths produce identical frames."""
    df["action"] = df["action"].str.lower()
    df = df.sort_values("date").reset_index(drop=True)
    df["signed_shares"] = df["shares"].where(df["action"] == "buy", -df["shares"])
    return df


def load_trades(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    return _normalize_trades(df)


def load_transactions(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["Date"])


# ── SQLite-backed loaders (system of record) ────────────────────────────────
# These return frames with columns identical to the CSV loaders so every
# downstream analytics call works byte-for-byte. Rows are read in insertion
# order (ORDER BY id == original CSV order) and then put through the exact same
# pandas sort as the CSV path, which keeps FIFO realized-P&L deterministic.


def load_trades_db(user_id: int, conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT ticker, action, shares, price, trade_date AS date FROM trades "
        "WHERE user_id = ? ORDER BY id",
        conn,
        params=(user_id,),
        parse_dates=["date"],
    )
    return _normalize_trades(df)


def load_transactions_db(user_id: int, conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        'SELECT txn_date AS "Date", amount_usd AS "Amount (USD)" FROM transactions '
        "WHERE user_id = ? ORDER BY id",
        conn,
        params=(user_id,),
        parse_dates=["Date"],
    )
