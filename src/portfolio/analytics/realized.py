"""FIFO realized P&L matcher.

Walks each ticker's trades in chronological order. Buys push lots onto a queue
with their buy price — the recorded execution price when present, else the
yfinance close on the trade date (see `prices.adjusted_trade_price`). Sells
consume lots from the front of the queue, splitting partial lots when the sell
size is smaller than the head lot. Each sell yields one row per matched lot.
"""
from __future__ import annotations

from collections import deque

import pandas as pd

from portfolio.data import prices as prices_mod

_EPS = 0.0001


def fifo_realized(trades_adj: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker in trades_adj["ticker"].unique():
        ticker_trades = trades_adj[trades_adj["ticker"] == ticker].sort_values("date")
        queue: deque[list] = deque()  # [shares_remaining, buy_price, buy_date]

        for _, t in ticker_trades.iterrows():
            if t["action"] == "buy":
                price = prices_mod.adjusted_trade_price(
                    ticker, t["date"], t.get("price"), t["split_factor"]
                )
                queue.append([t["adj_shares"], price, t["date"]])

            elif t["action"] == "sell":
                shares_left = abs(t["adj_shares"])
                sell_price = prices_mod.adjusted_trade_price(
                    ticker, t["date"], t.get("price"), t["split_factor"]
                )
                sell_date = t["date"]

                while shares_left > _EPS and queue:
                    lot_shares, lot_price, lot_date = queue[0]
                    matched = min(lot_shares, shares_left)
                    pnl = (
                        matched * (sell_price - lot_price)
                        if sell_price is not None and lot_price is not None
                        else 0.0
                    )

                    rows.append(
                        {
                            "ticker": ticker,
                            "shares": matched,
                            "buy_date": lot_date,
                            "sell_date": sell_date,
                            "buy_price": lot_price,
                            "sell_price": sell_price,
                            "realized_pnl": pnl,
                        }
                    )

                    queue[0][0] -= matched
                    shares_left -= matched
                    if queue[0][0] < _EPS:
                        queue.popleft()

    return pd.DataFrame(rows)


def realized_summary(realized: pd.DataFrame) -> pd.Series:
    if realized.empty:
        return pd.Series(dtype=float)
    return realized.groupby("ticker")["realized_pnl"].sum().sort_values(ascending=False).round(2)
