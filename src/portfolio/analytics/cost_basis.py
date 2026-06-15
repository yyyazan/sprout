"""Weighted-average cost basis and unrealized P&L for open positions.

Buy prices use the recorded execution price when present (what was actually
paid, normalized to today's split-adjusted terms via
`prices.adjusted_trade_price`), falling back to yfinance's split-adjusted close
on the trade date for older trades. Both that price and `adj_shares` are in
today's share-equivalent terms, so no further adjustment is needed.

Cost basis is computed from the FIFO lots that remain *after* sells are
matched (same lot accounting as `realized.fifo_realized`), so shares that were
sold no longer count toward the average. A position that is fully closed and
later re-opened therefore resets to its new lots, matching how brokers report
average cost.
"""
from __future__ import annotations

from collections import deque

import pandas as pd

from portfolio.data import prices as prices_mod

_EPS = 0.0001


def _remaining_lots(ticker_trades: pd.DataFrame, ticker: str) -> deque:
    """FIFO-walk a single ticker's trades, returning lots still held: [shares, price]."""
    queue: deque[list] = deque()
    for _, t in ticker_trades.sort_values("date").iterrows():
        if t["action"] == "buy":
            price = prices_mod.adjusted_trade_price(
                ticker, t["date"], t.get("price"), t["split_factor"]
            )
            queue.append([t["adj_shares"], price])
        elif t["action"] == "sell":
            shares_left = abs(t["adj_shares"])
            while shares_left > _EPS and queue:
                matched = min(queue[0][0], shares_left)
                queue[0][0] -= matched
                shares_left -= matched
                if queue[0][0] < _EPS:
                    queue.popleft()
    return queue


def weighted_avg_cost(trades_adj: pd.DataFrame, open_tickers: list[str]) -> pd.Series:
    """Weighted average cost basis per open ticker, over FIFO lots still held."""
    cost = {}
    for ticker in open_tickers:
        lots = _remaining_lots(trades_adj[trades_adj["ticker"] == ticker], ticker)
        priced = [(s, p) for s, p in lots if p is not None and s > _EPS]
        weight = sum(s for s, _ in priced)
        cost[ticker] = sum(s * p for s, p in priced) / weight if weight else 0.0
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
