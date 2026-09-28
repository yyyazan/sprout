"""Return attribution: which positions made the portfolio's $ move.

For each ticker we build a cumulative dollar P&L series

    pnl_i(t) = shares_i(t) × close_i(t)  +  Σ trade cash_i(<=t)

where trade cash is −adj_shares × price (a buy spends, a sell receives), priced
exactly like analytics/cash.py prices it. So pnl_i(t) is "what this ticker is
worth now, minus what it cost, plus what selling it paid back": realized and
unrealized P&L in one number, for open and closed positions alike.

Any window's contribution is then a plain difference, pnl_i(b) − pnl_i(a), and
the client can diff whatever window the chart shows without another request.

The identity that keeps this honest: summed over tickers,

    Σ_i pnl_i(t) = equity(t) + (cash(t) − net external flows(t) − offset)

so Σ_i Δpnl_i over a window equals the portfolio's $ change net of deposits and
withdrawals — the same number the chart's drag-measure shows.

Dividends aren't in the cash series, so they aren't here either; adding them
would break the identity. When dividends land in cash, add them to both.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

from portfolio.data import prices as prices_mod

TradePrice = Callable[[str, pd.Timestamp, float | None, float], float | None]


def cumulative_pnl_by_ticker(
    trades_adj: pd.DataFrame,
    price_history: dict[str, pd.Series],
    daily: pd.DatetimeIndex,
    trading_days: pd.DatetimeIndex,
    trade_price: TradePrice = prices_mod.adjusted_trade_price,
) -> pd.DataFrame:
    """Cumulative $ P&L per ticker, indexed by `trading_days`, one column per ticker.

    Mirrors timeseries.portfolio_equity (shares cumsum on the daily calendar,
    ffilled to trading days, × ffilled close) and cash.cash_timeseries (trade
    cash at the recorded or close price), so the columns sum back to the curve.
    """
    cols: dict[str, pd.Series] = {}
    for ticker in trades_adj["ticker"].unique():
        prices = price_history.get(ticker)
        if prices is None or prices.empty:
            continue  # unpriced: portfolio_equity skips it too
        tt = trades_adj[trades_adj["ticker"] == ticker]

        shares_by_day = tt.groupby("date")["adj_shares"].sum()
        shares = (
            shares_by_day.reindex(daily, fill_value=0.0).cumsum().clip(lower=0)
            .reindex(trading_days, method="ffill").fillna(0.0)
        )
        close = prices.dropna().reindex(trading_days, method="ffill")
        market_value = (shares * close).fillna(0.0)

        cash_by_day = pd.Series(0.0, index=daily)
        for _, r in tt.iterrows():
            price = trade_price(ticker, r["date"], r.get("price"), r["split_factor"])
            if price is None or r["date"] not in cash_by_day.index:
                continue
            cash_by_day.loc[r["date"]] += -r["adj_shares"] * price
        trade_cash = cash_by_day.cumsum().reindex(trading_days, method="ffill").fillna(0.0)

        cols[ticker] = market_value + trade_cash

    return pd.DataFrame(cols, index=trading_days, dtype=float)


def window_contributions(pnl_by_ticker: pd.DataFrame, start, end) -> pd.Series:
    """Each ticker's $ contribution between two dates (inclusive bars), largest first.

    Reference implementation of what the client does per window; used by tests
    and handy from a notebook.
    """
    a = pnl_by_ticker.loc[:start].iloc[-1] if len(pnl_by_ticker.loc[:start]) else 0.0
    b = pnl_by_ticker.loc[:end].iloc[-1]
    return (b - a).sort_values(ascending=False)
