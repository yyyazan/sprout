"""PortfolioSnapshot → JSON-able dicts, one builder per endpoint.

Charts cross the boundary as raw series ({x, y, name}); the Svelte side
assembles Plotly figures using the theme mirrored from viz/figures.py. Every
builder returns plain Python types (no numpy / NaN) so FastAPI can serialize
directly.
"""
from __future__ import annotations

import math
import time

import numpy as np
import pandas as pd

from portfolio.pipeline import PortfolioSnapshot
from portfolio.data import prices as prices_mod
from portfolio.analytics.cards import _spot_move

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
    # Headline total from LIVE spot prices (same source as the positions and
    # allocation below) rather than the last point of the daily-close equity
    # curve — otherwise the big number lags the per-holding cards intraday.
    # (.sum() skips NaN, so an unpriced holding just drops out, as it already
    # does from the cards/allocation.)
    equities = float(s.pnl["market_value"].sum())
    portfolio_value = equities + float(s.free_cash)
    unrealized_pnl = float(s.pnl["unrealized_pnl"].sum())
    realized_pnl = float(s.realized_summary.sum())
    total_pnl = unrealized_pnl + realized_pnl

    return {
        "greeting": greeting_for(period),
        "period": period,
        "kpis": {
            "cash": _py(s.free_cash),
            "equities": _py(equities),
            "portfolio_value": _py(portfolio_value),
            "total_pnl": _py(total_pnl),
            "realized_pnl": _py(realized_pnl),
            "unrealized_pnl": _py(unrealized_pnl),
        },
        "goal": {"current": _py(s.monthly_deposits), "target": MONTHLY_SAVINGS_TARGET},
        "dividends": s.dividends,
        "allocation": _allocation(s.pnl["market_value"], max(float(s.free_cash), 0.0)),
        "equity_curve": _xy(s.portfolio_value_ts, 2),
        # Cumulative net external cash in (deposits − withdrawals), aligned to the
        # equity curve. Lets the chart strip deposits out of a window's $ gain so
        # the headline reads earnings, not balance growth.
        "net_invested": _xy(s.net_invested, 2),
        # Parallel SPY portfolio ($): the same cash flows invested in SPY instead.
        # This is the HONEST dollar benchmark — the gap vs equity_curve is real
        # out/under-performance, not deposits (a TWR-rebased line would be ~99%
        # deposits and misleading). Used for the chart's Value-mode SPY overlay.
        "spy_curve": _xy(s.spy_ts, 2),
        # Time-weighted return (decimals, e.g. 0.184 = +18.4%) — apples-to-apples
        # % comparison for the chart's Return mode. Same daily index, aligned by date.
        "twr": {
            "portfolio": _xy(s.twr_portfolio, 5),
            "spy": _xy(s.twr_spy, 5),
        },
        "cards": [{k: _py(v) for k, v in c.items()} for c in s.cards],
    }


# Live momentum is intentionally OUTSIDE the compute-once snapshot cache so a
# mid-day check reflects right-now spot prices. A short TTL bounds how often we
# hit yfinance regardless of reloads/polling.
_MOM_TTL_SECONDS = 45.0
_mom_cache: dict = {"ts": 0.0, "key": None, "data": None}


def momentum_payload(s: PortfolioSnapshot) -> dict:
    """Fresh per-holding intraday momentum (spot vs prior-session close).

    Quotes are fetched in one batched call with `max_age=0` (force fresh),
    cached only for `_MOM_TTL_SECONDS`. Reference closes come from the (cheap,
    cached) daily-close history; only spot is forced fresh.
    """
    tickers = [str(t) for t in s.pnl.index]
    key = tuple(tickers)
    now = time.time()
    if _mom_cache["data"] is not None and _mom_cache["key"] == key and (now - _mom_cache["ts"] < _MOM_TTL_SECONDS):
        return _mom_cache["data"]

    quotes = prices_mod.quotes(tickers, max_age=0.0)  # force fresh quotes this cycle
    moves: dict = {}
    for t in tickers:
        hist = prices_mod.history(t)
        spot = quotes[t]["price"]
        day = _spot_move(hist, spot, 1)
        week = _spot_move(hist, spot, 5)
        moves[t] = {
            "day_pct": round(day * 100, 2) if day is not None else None,
            "week_pct": round(week * 100, 2) if week is not None else None,
            "spot": round(float(spot), 2) if spot is not None else None,
        }

    data = {"as_of": now, "ttl": _MOM_TTL_SECONDS, "moves": moves}
    _mom_cache.update(ts=now, key=key, data=data)
    return data


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
