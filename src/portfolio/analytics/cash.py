"""Free cash reconstruction.

The double-counting bug fix lives here: cash at any point in time is

    cash(t) = Σ deposits(<=t) − Σ withdrawals(<=t)
              − Σ buy_notional(<=t) + Σ sell_proceeds(<=t)

NOT (deposits − withdrawals) added to portfolio equity separately — that would
double-count money that's been deployed into stocks.

A single `CASH_RECONCILIATION_OFFSET` (below) is added as the final step of both
`free_cash` (scalar KPI) and `cash_timeseries` so the dashboard matches what the
broker actually displays. This lives only in code — transactions.csv / trades.csv
are never edited to absorb the drift (that would corrupt the audit trail).
"""
from __future__ import annotations

import pandas as pd

from portfolio.data import prices as prices_mod

# Untraced cash drift (FX rounding + legacy fees). Adjust to match
# actual broker cash. Last reconciled: 2026-05-28, broker cash = $3.
CASH_RECONCILIATION_OFFSET = -107.0


def _trade_cash_impact(trades_adj: pd.DataFrame) -> float:
    """Net cash spent (negative) or received (positive) across all trades."""
    total = 0.0
    for _, r in trades_adj.iterrows():
        price = prices_mod.price_on_date(r["ticker"], r["date"])
        if price is None:
            continue
        total += -r["adj_shares"] * price
    return total


def free_cash(trades_adj: pd.DataFrame, txn: pd.DataFrame) -> float:
    """Scalar free cash, reconciled to the broker via CASH_RECONCILIATION_OFFSET."""
    bank_net = float(txn["Amount (USD)"].sum())
    trade_cash = _trade_cash_impact(trades_adj)
    return bank_net + trade_cash + CASH_RECONCILIATION_OFFSET


def cash_timeseries(
    trades_adj: pd.DataFrame, txn: pd.DataFrame, calendar: pd.DatetimeIndex
) -> pd.Series:
    """Daily cash balance over `calendar`, reconciled via CASH_RECONCILIATION_OFFSET."""
    trade_cash_daily = pd.Series(0.0, index=calendar)
    for _, r in trades_adj.iterrows():
        price = prices_mod.price_on_date(r["ticker"], r["date"])
        if price is None:
            continue
        if r["date"] in trade_cash_daily.index:
            trade_cash_daily.loc[r["date"]] += -r["adj_shares"] * price

    txn_daily = txn.groupby("Date")["Amount (USD)"].sum().reindex(calendar, fill_value=0.0)
    # Level shift after the cumulative sum — applied once, not distributed across rows.
    return (txn_daily + trade_cash_daily).cumsum() + CASH_RECONCILIATION_OFFSET
