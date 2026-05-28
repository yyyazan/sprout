"""Weighted-average cost basis and unrealized P&L for open positions.

Trades.csv has no price column — buy prices are inferred from yfinance's
split-adjusted close on the trade date. Since both `adj_shares` (post-split)
and `price_on_date` (back-adjusted) are in today's share-equivalent terms,
no further adjustment is needed.
"""
from __future__ import annotations

import pandas as pd

from portfolio.data import prices as prices_mod


def weighted_avg_cost(trades_adj: pd.DataFrame, open_tickers: list[str]) -> pd.Series:
    """Weighted average cost basis per open ticker, computed from buys only."""
    buys = trades_adj[
        (trades_adj["ticker"].isin(open_tickers)) & (trades_adj["action"] == "buy")
    ].copy()
    buys["price_paid"] = buys.apply(
        lambda r: prices_mod.price_on_date(r["ticker"], r["date"]), axis=1
    )

    cost = {}
    for ticker in open_tickers:
        tb = buys[buys["ticker"] == ticker]
        weight = tb["adj_shares"].sum()
        if weight == 0:
            cost[ticker] = 0.0
        else:
            cost[ticker] = (tb["price_paid"] * tb["adj_shares"]).sum() / weight
    return pd.Series(cost)


def unrealized_pnl(
    open_positions: pd.Series,
    cost_basis: pd.Series,
    spot_prices: dict[str, float],
) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "shares": open_positions,
            "cost_basis": cost_basis,
            "current_price": pd.Series(spot_prices),
        }
    )
    df["total_invested"] = df["cost_basis"] * df["shares"]
    df["market_value"] = df["current_price"] * df["shares"]
    df["unrealized_pnl"] = df["market_value"] - df["total_invested"]
    df["return_pct"] = (df["unrealized_pnl"] / df["total_invested"] * 100).round(2)
    return df.sort_values("unrealized_pnl", ascending=False)
