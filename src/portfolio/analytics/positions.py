"""Net positions and split-adjustment.

yfinance back-adjusts all historical prices through every split it knows about,
so a pre-split buy at price P shows up as P / split_ratio. To make our share
counts comparable, we scale forward by every split that occurred *after* the
trade date. Splits before the trade are already baked into the adjusted price,
so the share count stays as transacted.
"""
from __future__ import annotations

import pandas as pd


def cumulative_split_factor(splits: pd.Series, trade_date: pd.Timestamp) -> float:
    """Product of split ratios for splits strictly after `trade_date`."""
    if splits.empty:
        return 1.0
    future = splits[splits.index > trade_date]
    return float(future.prod()) if not future.empty else 1.0


def split_adjust(trades: pd.DataFrame, splits_by_ticker: dict[str, pd.Series]) -> pd.DataFrame:
    """Add `split_factor` and `adj_shares` columns to a trades frame."""
    out = trades.copy()
    out["split_factor"] = out.apply(
        lambda r: cumulative_split_factor(
            splits_by_ticker.get(r["ticker"], pd.Series(dtype=float)), r["date"]
        ),
        axis=1,
    )
    out["adj_shares"] = out["signed_shares"] * out["split_factor"]
    return out


def net_positions(trades_adj: pd.DataFrame) -> pd.Series:
    """Sum adj_shares per ticker. Positive = open position."""
    return trades_adj.groupby("ticker")["adj_shares"].sum().round(4)


def open_positions(trades_adj: pd.DataFrame, threshold: float = 0.01) -> pd.Series:
    """Tickers with net adj_shares > threshold, sorted descending."""
    net = net_positions(trades_adj)
    return net[net > threshold].sort_values(ascending=False)
