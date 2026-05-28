"""Max drawdown and Sharpe — computed on TWR series for apples-to-apples comparison."""
from __future__ import annotations

import pandas as pd


def max_drawdown(twr_series: pd.Series) -> float:
    """Most-negative drawdown of the cumulative-return series. Returns a decimal (-0.23 = -23%)."""
    equity = 1 + twr_series
    peak = equity.expanding().max()
    return float(((equity - peak) / peak).min())


def sharpe(twr_series: pd.Series, rf: float = 0.0, periods_per_year: int = 252) -> float:
    """Annualized Sharpe from a cumulative TWR series.

    Notes:
      The notebook computes Sharpe from cumulative TWR directly (not daily
      returns). We preserve that for parity — it's a "shape" Sharpe, not a
      textbook one, but it's what the existing KPI shows.
    """
    if twr_series.std() == 0 or pd.isna(twr_series.std()):
        return 0.0
    return float((twr_series.mean() - rf) / twr_series.std())
