"""Lab — the retail-quant learning bench (/lab route).

Contained skeleton for screener / factors / backtesting / options / paper
trading. Two endpoints are real today, both running entirely on data the app
already caches (no new network calls):

- /api/lab/backtest — SMA-crossover vs buy-and-hold on the cached daily
  closes. Deliberately the "hello world" of backtests: enough to learn equity
  curves, drawdown, and why time-in-market matters. vectorbt comes later.
- /api/lab/factors — CAPM regression (alpha/beta/R²) of the portfolio's daily
  TWR returns against SPY's. Fama-French 3/5-factor needs the Ken French data
  library and is a planned upgrade, not built yet.

Everything here is analysis only. Nothing in the Lab ever places an order with
a broker — paper trading is the ceiling (same safety rule as TradeTicket).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query

from portfolio.data import db as db_mod, prices as prices_mod

from api import state
from api.serialize import _py

router = APIRouter(prefix="/api/lab", tags=["lab"])

_MAX_POINTS = 400  # downsample curves so payloads stay chart-sized


def _curve(series: pd.Series) -> dict:
    step = max(1, len(series) // _MAX_POINTS)
    s = series.iloc[::step]
    if s.index[-1] != series.index[-1]:  # always keep the final point
        s = pd.concat([s, series.iloc[[-1]]])
    return {
        "x": [d.strftime("%Y-%m-%d") for d in s.index],
        "y": [_py(round(float(v), 4)) for v in s.to_numpy()],
    }


def _max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1).min())


@router.get("/backtest")
def backtest(
    ticker: str = Query(..., min_length=1, max_length=10),
    fast: int = Query(20, ge=2, le=200),
    slow: int = Query(50, ge=3, le=300),
    years: int = Query(5, ge=1, le=15),
):
    """SMA(fast)/SMA(slow) crossover, long-or-flat, daily closes, no costs.

    The signal is shifted one day: you trade at tomorrow's close on today's
    cross. Forgetting that shift is look-ahead bias — the classic backtest sin.
    """
    if fast >= slow:
        return {"ok": False, "error": "fast SMA must be shorter than slow"}

    px = prices_mod.history(ticker.upper())
    if px.empty:
        return {"ok": False, "error": f"no price history for {ticker.upper()}"}
    px = px[px.index >= px.index.max() - pd.DateOffset(years=years)]
    if len(px) < slow + 20:
        return {"ok": False, "error": "not enough history for that SMA window"}

    in_market = (px.rolling(fast).mean() > px.rolling(slow).mean()).shift(1).fillna(False)
    ret = px.pct_change().fillna(0.0)
    strat = (1 + ret.where(in_market, 0.0)).cumprod()
    hold = (1 + ret).cumprod()

    n = len(strat)
    cagr = lambda eq: float(eq.iloc[-1] ** (252 / n) - 1) if n else None  # noqa: E731
    return {
        "ok": True,
        "ticker": ticker.upper(),
        "params": {"fast": fast, "slow": slow, "years": years},
        "strategy": _curve(strat),
        "buy_hold": _curve(hold),
        "stats": {
            "strat_return": _py(round(float(strat.iloc[-1] - 1) * 100, 1)),
            "hold_return": _py(round(float(hold.iloc[-1] - 1) * 100, 1)),
            "strat_cagr": _py(round(cagr(strat) * 100, 1)),
            "hold_cagr": _py(round(cagr(hold) * 100, 1)),
            "strat_max_dd": _py(round(_max_drawdown(strat) * 100, 1)),
            "hold_max_dd": _py(round(_max_drawdown(hold) * 100, 1)),
            "trades": int(in_market.astype(int).diff().abs().sum()),
            "exposure_pct": _py(round(float(in_market.mean()) * 100, 0)),
        },
    }


@router.get("/factors")
def factors(user_id: int = db_mod.DEFAULT_USER_ID):
    """CAPM single-factor regression: portfolio daily TWR returns vs SPY's.

    beta = market sensitivity, alpha = annualized return unexplained by the
    market, R² = how much of the variance the market explains. The honest
    retail expectation: beta ≈ 1, alpha ≈ 0, and most "alpha" is noise — the
    upgrade path (Fama-French 3/5-factor) shows how much of it is really
    size/value/momentum exposure.
    """
    s = state.get_snapshot(user_id)
    rp = (1 + s.twr_portfolio).pct_change()
    rm = (1 + s.twr_spy).pct_change()
    df = pd.concat([rp.rename("p"), rm.rename("m")], axis=1).dropna()
    if len(df) < 60:
        return {"ok": False, "error": "need ≥60 trading days of history"}

    var_m = float(df["m"].var())
    if not var_m or math.isnan(var_m):
        return {"ok": False, "error": "benchmark variance is zero"}
    beta = float(df["p"].cov(df["m"]) / var_m)
    alpha_daily = float(df["p"].mean() - beta * df["m"].mean())
    corr = float(np.corrcoef(df["p"], df["m"])[0, 1])

    return {
        "ok": True,
        "n_days": len(df),
        "beta": _py(round(beta, 2)),
        "alpha_annual_pct": _py(round(alpha_daily * 252 * 100, 1)),
        "r_squared": _py(round(corr * corr, 2)),
        "sharpe_portfolio": _py(round(s.sharpe_portfolio, 2)),
        "sharpe_spy": _py(round(s.sharpe_spy, 2)),
        "max_dd_portfolio_pct": _py(round(s.max_drawdown_portfolio * 100, 1)),
        "max_dd_spy_pct": _py(round(s.max_drawdown_spy * 100, 1)),
    }
