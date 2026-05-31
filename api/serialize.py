"""PortfolioSnapshot → JSON-able dicts, one builder per endpoint.

Charts cross the boundary as raw series ({x, y, name}); the Svelte side
assembles Plotly figures using the theme mirrored from viz/figures.py. Every
builder returns plain Python types (no numpy / NaN) so FastAPI can serialize
directly.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from portfolio.pipeline import PortfolioSnapshot

from api.config import MONTHLY_SAVINGS_TARGET
from api.greeting import greeting_for


def _py(v):
    """Coerce numpy/pandas scalars to JSON-safe Python values (NaN/inf → None)."""
    if v is None:
        return None
    if isinstance(v, (np.generic,)):
        v = v.item()
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def _last(series: pd.Series, default=None):
    return float(series.iloc[-1]) if len(series) else default


def _xy(series: pd.Series, round_y: int | None = None) -> dict:
    idx = pd.DatetimeIndex(series.index)
    x = [d.strftime("%Y-%m-%d") for d in idx]
    vals = series.to_numpy(dtype=float)
    if round_y is not None:
        vals = np.round(vals, round_y)
    y = [None if (math.isnan(v) or math.isinf(v)) else float(v) for v in vals]
    return {"x": x, "y": y}


def _allocation(market_value: pd.Series, cash: float) -> dict:
    labels = [str(t) for t in market_value.index]
    values = [round(float(v), 2) for v in market_value.to_numpy()]
    if cash > 0:
        labels.append("Cash")
        values.append(round(float(cash), 2))
    return {"labels": labels, "values": values}


def dashboard_payload(s: PortfolioSnapshot, period: str) -> dict:
    portfolio_value = _last(s.portfolio_value_ts, default=float(s.free_cash))
    total_pnl = float(s.pnl["unrealized_pnl"].sum()) + float(s.realized_summary.sum())
    you_pct = _last(s.twr_portfolio)
    spy_pct = _last(s.twr_spy)
    spy_delta = (you_pct - spy_pct) if (you_pct is not None and spy_pct is not None) else None

    return {
        "greeting": greeting_for(period),
        "period": period,
        "kpis": {
            "cash": _py(s.free_cash),
            "spy_delta": _py(spy_delta),       # decimal (e.g. 0.17 = +17pp)
            "portfolio_value": _py(portfolio_value),
            "total_pnl": _py(total_pnl),
        },
        "goal": {"current": _py(s.monthly_deposits), "target": MONTHLY_SAVINGS_TARGET},
        "allocation": _allocation(s.pnl["market_value"], max(float(s.free_cash), 0.0)),
        "equity_curve": _xy(s.portfolio_value_ts, 2),
        "cards": [{k: _py(v) for k, v in c.items()} for c in s.cards],
    }


def investments_payload(s: PortfolioSnapshot) -> dict:
    bench_twr = {"SPY": s.twr_spy}
    if not s.twr_qqq.empty:
        bench_twr["QQQ"] = s.twr_qqq

    # Drawdown (mirrors figures.drawdown_area).
    equity = 1 + s.twr_portfolio
    peak = equity.expanding().max()
    dd = (equity - peak) / peak * 100

    # P&L bars sorted ascending (mirrors figures.pnl_bars).
    pnl_sorted = s.pnl["unrealized_pnl"].sort_values()

    df = s.pnl.reset_index().rename(columns={"index": "ticker"})
    total_mv = float(df["market_value"].sum())
    df["weight"] = (df["market_value"] / total_mv * 100) if total_mv else 0.0
    positions = [
        {k: _py(v) for k, v in row.items()}
        for row in df.to_dict("records")
    ]

    return {
        "kpis": {
            "twr": _py(_last(s.twr_portfolio, 0.0)),
            "max_drawdown": _py(s.max_drawdown_portfolio),
            "sharpe": _py(s.sharpe_portfolio),
            "spy_twr": _py(_last(s.twr_spy, 0.0)),
            "spy_dd": _py(s.max_drawdown_spy),
            "spy_sharpe": _py(s.sharpe_spy),
        },
        "charts": {
            "twr": {
                "portfolio": _xy(s.twr_portfolio * 100, 3),
                "benchmarks": {label: _xy(series * 100, 3) for label, series in bench_twr.items()},
            },
            "drawdown": _xy(dd, 3),
            "pnl_bars": {
                "tickers": [str(t) for t in pnl_sorted.index],
                "values": [round(float(v), 2) for v in pnl_sorted.to_numpy()],
            },
            "allocation": _allocation(s.pnl["market_value"], max(float(s.free_cash), 0.0)),
        },
        "positions": positions,
    }


def garden_payload(s: PortfolioSnapshot, period: str) -> dict:
    positions = [
        {k: _py(v) for k, v in c.items()} for c in s.cards if not c.get("is_joker")
    ]
    return {"positions": positions, "period": period}


def realized_payload(s: PortfolioSnapshot) -> list[dict]:
    df = s.realized.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.DatetimeIndex(df[col]).strftime("%Y-%m-%d")
    return [{k: _py(v) for k, v in row.items()} for row in df.to_dict("records")]
