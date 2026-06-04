"""GET /api/stock/{ticker} — per-ticker MARKET data for the expanded stock
deep-view: quote, fundamentals, 52-week range, analyst target, and the daily
close line. Position data (shares/cost/value/P&L/weight) stays on the frontend,
which already has it from the dashboard payload.

yfinance `.info` is slow and rate-limited, so it's memoised in-process for 30
minutes. The price line reuses the already-cached prices module.
"""
from __future__ import annotations

import time

import yfinance as yf
from fastapi import APIRouter

from portfolio.data import prices as prices_mod
from api.serialize import _py

router = APIRouter(prefix="/api", tags=["stock"])

_INFO_TTL = 1800.0  # 30 min — .info is slow / rate-limited
_info_cache: dict[str, tuple[float, dict]] = {}


def _info(ticker: str) -> dict:
    now = time.time()
    hit = _info_cache.get(ticker)
    if hit is not None and now - hit[0] < _INFO_TTL:
        return hit[1]
    try:
        info = yf.Ticker(prices_mod.yf_symbol(ticker)).info or {}
    except Exception:
        info = {}
    _info_cache[ticker] = (now, info)
    return info


def _first(info: dict, *keys):
    for k in keys:
        v = info.get(k)
        if v is not None:
            return v
    return None


@router.get("/stock/{ticker}")
def stock(ticker: str):
    ticker = ticker.upper()
    info = _info(ticker)

    price = _first(info, "currentPrice", "regularMarketPrice")
    div_rate = info.get("dividendRate")
    div_yld = (div_rate / price * 100) if (div_rate and price) else None

    # yfinance's trailingPE field is unreliable (esp. for negative earnings:
    # RKLB reports PE -10823 while EPS is -0.32). Derive PE locally from
    # price / EPS so the two are always consistent.
    eps = _first(info, "trailingEps", "forwardEps")
    pe = (price / eps) if (price is not None and eps not in (None, 0)) else None

    # real split-adjusted daily closes (already cached by the prices module)
    history = []
    try:
        hist = prices_mod.history(ticker)
        for d, v in hist.tail(1300).items():
            if v is None:
                continue
            c = _py(round(float(v), 2))
            if c is not None:
                history.append({"t": d.strftime("%Y-%m-%d"), "c": c})
    except Exception:
        history = []

    return {
        "ticker": ticker,
        "sector": info.get("sector") or info.get("industry") or "",
        "price": _py(price),
        "open": _py(_first(info, "open", "regularMarketOpen")),
        "prevClose": _py(_first(info, "previousClose", "regularMarketPreviousClose")),
        "dayLow": _py(_first(info, "dayLow", "regularMarketDayLow")),
        "dayHigh": _py(_first(info, "dayHigh", "regularMarketDayHigh")),
        "week52Low": _py(info.get("fiftyTwoWeekLow")),
        "week52High": _py(info.get("fiftyTwoWeekHigh")),
        "volume": _py(_first(info, "volume", "regularMarketVolume")),
        "avgVolume": _py(_first(info, "averageVolume", "averageVolume10days")),
        "marketCap": _py(info.get("marketCap")),
        "pe": _py(round(pe, 1)) if pe is not None else None,
        "eps": _py(eps),
        "divYield": _py(round(div_yld, 2)) if div_yld is not None else None,
        "beta": _py(info.get("beta")),
        "target": _py(info.get("targetMeanPrice")),
        "rating": info.get("recommendationKey") or "",
        "history": history,
    }
