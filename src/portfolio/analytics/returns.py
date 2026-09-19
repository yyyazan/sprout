"""Time-Weighted Return.

TWR strips out the effect of deposits/withdrawals so the curve only reflects
holding performance. Per-day:

    r_t = (V_t - CF_t) / V_{t-1}        when V_{t-1} > 0
    r_t = 1                             otherwise

where CF_t is the *external* cash flow on day t (txn deposits/withdrawals,
NOT trade cash — trades are internal portfolio rotations). Cumulative product
gives the cumulative growth factor; subtract 1 for cumulative return.
"""
from __future__ import annotations

import pandas as pd


def twr(
    total_value_ts: pd.Series,
    txn: pd.DataFrame,
    trading_days: pd.DatetimeIndex,
    daily: pd.DatetimeIndex,
) -> pd.Series:
    """Cumulative TWR series (decimal returns; 0.0 = breakeven, 0.10 = +10%)."""
    txn_daily = txn.groupby("Date")["Amount (USD)"].sum().reindex(daily, fill_value=0.0)
    cf_cumul_td = txn_daily.cumsum().reindex(trading_days, method="ffill").fillna(0.0)
    cf_per_td = cf_cumul_td.diff()
    cf_per_td.iloc[0] = cf_cumul_td.iloc[0]

    # Blank the non-positive denominators BEFORE dividing, not after. A young
    # portfolio's value series can be object dtype (and starts with real 0.0s
    # on the days before the first fill), which puts pandas on a Python-level
    # division that raises ZeroDivisionError instead of yielding inf/NaN.
    v = pd.to_numeric(total_value_ts, errors="coerce")
    v_prev = v.shift(1).where(lambda prev: prev > 0)
    ratio = ((v - cf_per_td) / v_prev).fillna(1.0)
    return ratio.cumprod() - 1


def benchmark_twr(bench_prices: pd.Series, first_day: pd.Timestamp) -> pd.Series:
    """Buy-and-hold % from `first_day`. Equals TWR of a parallel benchmark portfolio."""
    return bench_prices / bench_prices.loc[first_day] - 1
