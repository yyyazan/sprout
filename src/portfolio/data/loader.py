"""Load trades.csv and transactions.csv into normalized DataFrames.

trades.csv schema:        ticker, action, shares, date
transactions.csv schema:  Date, Amount (USD)

Both files use ISO dates (yyyy-mm-dd). A transaction's direction is inferred
from the sign of Amount (USD): positive = deposit, negative = withdrawal.
Broker-drift reconciliation lives in code (cash.CASH_RECONCILIATION_OFFSET),
never as fudge rows here.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_trades(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df["action"] = df["action"].str.lower()
    df = df.sort_values("date").reset_index(drop=True)
    df["signed_shares"] = df["shares"].where(df["action"] == "buy", -df["shares"])
    return df


def load_transactions(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["Date"])
