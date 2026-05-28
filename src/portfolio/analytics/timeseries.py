"""Daily portfolio value and parallel-benchmark reconstruction.

The portfolio time series is built by:
  1. For each ticker, computing daily share counts via cumsum of adj_shares
     over a full daily calendar (so weekend/holiday trades aren't lost).
  2. Reindexing to trading days with forward-fill.
  3. Multiplying by daily close prices and summing across tickers.
  4. Adding daily cash (see analytics/cash.cash_timeseries).

The "parallel" benchmark answers: what if every $ of every transaction had gone
into SPY/QQQ on the same day? Each txn buys (or sells) fractional benchmark
shares at that day's close. Apples-to-apples vs the real portfolio.
"""
from __future__ import annotations

import pandas as pd


def daily_calendar(
    trades: pd.DataFrame, txn: pd.DataFrame, trading_days: pd.DatetimeIndex
) -> pd.DatetimeIndex:
    """Full daily calendar covering every trade, transaction, and trading day.

    Extends past the last market close if a deposit or trade lands on a weekend.
    """
    start = trades["date"].min()
    end = max(trading_days.max(), txn["Date"].max(), trades["date"].max())
    return pd.date_range(start=start, end=end, freq="D")


def portfolio_equity(
    trades_adj: pd.DataFrame,
    price_history: dict[str, pd.Series],
    daily: pd.DatetimeIndex,
    trading_days: pd.DatetimeIndex,
) -> pd.Series:
    """Daily equity (sum of holdings × close) over `trading_days`."""
    equity = pd.Series(0.0, index=trading_days)
    for ticker in trades_adj["ticker"].unique():
        prices = price_history.get(ticker)
        if prices is None or prices.empty:
            continue
        trade_by_day = trades_adj[trades_adj["ticker"] == ticker].groupby("date")["adj_shares"].sum()
        cumul = trade_by_day.reindex(daily, fill_value=0.0).cumsum().clip(lower=0)
        shares_ts = cumul.reindex(trading_days, method="ffill")
        prices_ts = prices.reindex(trading_days, method="ffill")
        equity = equity.add((shares_ts * prices_ts).fillna(0), fill_value=0.0)
    return equity


def benchmark_parallel(
    bench_prices: pd.Series,
    txn: pd.DataFrame,
    daily: pd.DatetimeIndex,
    trading_days: pd.DatetimeIndex,
) -> pd.Series:
    """Daily value of a parallel portfolio that mirrors txn flows into `bench_prices`."""
    shares_delta = pd.Series(0.0, index=daily)
    for _, r in txn.iterrows():
        date, amount = r["Date"], r["Amount (USD)"]
        valid = bench_prices[bench_prices.index <= date]
        if valid.empty or date not in shares_delta.index:
            continue
        shares_delta.loc[date] += amount / float(valid.iloc[-1])
    shares_ts = shares_delta.cumsum().reindex(trading_days, method="ffill").fillna(0.0)
    return shares_ts * bench_prices


def trim_to_first_meaningful_day(
    total_portfolio_ts: pd.Series, threshold: float = 10.0
) -> pd.Timestamp:
    """First day on which the portfolio is non-trivially funded."""
    nonzero = total_portfolio_ts[total_portfolio_ts > threshold]
    return nonzero.index[0] if len(nonzero) else total_portfolio_ts.index[0]


def capital_flows(
    txn: pd.DataFrame, daily: pd.DatetimeIndex, trading_days: pd.DatetimeIndex
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Cumulative deposits, withdrawals (positive), and net invested over time."""
    dep = txn[txn["Amount (USD)"] > 0].groupby("Date")["Amount (USD)"].sum()
    wd = txn[txn["Amount (USD)"] < 0].groupby("Date")["Amount (USD)"].sum().abs()

    def _to_trading(s: pd.Series) -> pd.Series:
        return (
            s.reindex(daily, fill_value=0.0)
            .cumsum()
            .reindex(trading_days, method="ffill")
            .fillna(0.0)
        )

    deposits = _to_trading(dep)
    withdrawals = _to_trading(wd)
    return deposits, withdrawals, deposits - withdrawals
