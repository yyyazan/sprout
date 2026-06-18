"""Watchlist — non-held tickers on the radar (the stock view's "+ Watch").

GET returns light quotes (price + day move) so the sidebar rail can render
rows without another round-trip. Quotes come from the shared batched
``prices.quotes`` cache — watchlist names aren't in the holdings momentum poll.
"""
from __future__ import annotations

import re

from fastapi import APIRouter
from pydantic import BaseModel

from portfolio.data import db as db_mod, prices as prices_mod
from portfolio.analytics.cards import _spot_move  # reuse holdings' exact day/week-move math
from api.serialize import _py

router = APIRouter(prefix="/api", tags=["watchlist"])

_TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,10}$")

_QUOTE_TTL = 300.0  # 5 min — rail strips, not a trading terminal


def _payload(conn, user_id: int) -> list[dict]:
    tickers = db_mod.watchlist_tickers(conn, user_id)
    quotes = prices_mod.quotes(tickers, max_age=_QUOTE_TTL)
    hists = prices_mod.histories(tickers)  # daily closes → week move (D/W toggle)
    out = []
    for t in tickers:
        try:
            name = prices_mod.profile(t).get("name") or t
        except Exception:
            name = t
        price, prev = quotes[t]["price"], quotes[t]["prev_close"]
        week = _spot_move(hists.get(t), price, 5)  # spot vs close 5 sessions ago
        out.append({
            "ticker": t,
            "name": name,
            "price": _py(round(price, 2)) if price is not None else None,
            "dayPct": _py(round((price / prev - 1) * 100, 2)) if (price and prev) else None,
            "weekPct": _py(round(week * 100, 2)) if week is not None else None,
        })
    return out


@router.get("/watchlist")
def watchlist(user_id: int = db_mod.DEFAULT_USER_ID):
    return _payload(db_mod.connect(), user_id)


class WatchIn(BaseModel):
    ticker: str


@router.post("/watchlist")
def add(body: WatchIn, user_id: int = db_mod.DEFAULT_USER_ID):
    ticker = (body.ticker or "").strip().upper()
    if not _TICKER_RE.match(ticker):
        return {"ok": False, "error": "Invalid ticker.", "watchlist": None}
    conn = db_mod.connect()
    db_mod.watchlist_add(conn, ticker, user_id)
    return {"ok": True, "error": None, "watchlist": _payload(conn, user_id)}


@router.delete("/watchlist/{ticker}")
def remove(ticker: str, user_id: int = db_mod.DEFAULT_USER_ID):
    conn = db_mod.connect()
    db_mod.watchlist_remove(conn, ticker.strip().upper(), user_id)
    return {"ok": True, "error": None, "watchlist": _payload(conn, user_id)}
