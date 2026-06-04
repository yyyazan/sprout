"""Monthly dividend income from current positions.

For each holding the annual dividend per share is the FORWARD rate (yfinance
``info["dividendRate"]``, captured in the cached profile) when available, else
the TRAILING 12-month sum of actual per-share payments (``Ticker.dividends``).
Times shares -> annual $; / 12 -> monthly $. Non-payers drop out.

Returns the shape the dashboard's Dividend Wraith consumes:

    {items: [{t, name, value, yieldPct, annual, monthly}, ...],
     monthlyTotal, annualTotal, yieldOnValue}

`items` are payers only, biggest monthly first. `yieldOnValue` is the blended
yield over the dividend-paying holdings (matches what the wraith's core shows).
"""
from __future__ import annotations

import pandas as pd

from portfolio.data import prices as prices_mod


def _ttm_per_share(ticker: str, now: pd.Timestamp) -> float:
    """Trailing 12-month dividends per share (sum of actual payments)."""
    div = prices_mod.dividends(ticker)
    if div is None or div.empty:
        return 0.0
    recent = div[div.index >= now - pd.Timedelta(days=365)]
    return float(recent.sum()) if not recent.empty else 0.0


def _annual_per_share(ticker: str, now: pd.Timestamp) -> float:
    """Forward annual rate if the cached profile has it, else trailing-12-month."""
    try:
        fwd = prices_mod.profile(ticker).get("dividend_rate")
        fwd = float(fwd) if fwd is not None else 0.0
    except (TypeError, ValueError, Exception):
        fwd = 0.0
    if fwd > 0:
        return fwd
    try:
        return _ttm_per_share(ticker, now)
    except Exception:
        return 0.0


def monthly_dividends(pnl, cards) -> dict:
    """Per-holding monthly dividends + totals for the dashboard payload."""
    now = pd.Timestamp.now()
    names = {
        c["ticker"]: (c.get("company_name") or c["ticker"])
        for c in cards
        if not c.get("is_joker")
    }

    items: list[dict] = []
    for ticker, row in pnl.iterrows():
        t = str(ticker)
        shares = float(row["shares"])
        value = float(row["market_value"])
        if shares <= 0:
            continue
        annual = shares * _annual_per_share(t, now)
        if annual <= 0:
            continue
        items.append({
            "t": t,
            "name": names.get(t, t),
            "value": round(value, 2),
            "yieldPct": round(annual / value * 100, 2) if value else 0.0,
            "annual": round(annual, 2),
            "monthly": round(annual / 12, 2),
        })

    items.sort(key=lambda d: d["monthly"], reverse=True)
    annual_total = round(sum(d["annual"] for d in items), 2)
    invested = sum(d["value"] for d in items)
    return {
        "items": items,
        "monthlyTotal": round(sum(d["monthly"] for d in items), 2),
        "annualTotal": annual_total,
        "yieldOnValue": round(annual_total / invested * 100, 2) if invested else 0.0,
    }
