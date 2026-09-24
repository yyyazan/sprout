"""Sidebar lists — user-named ticker lists (the stock view's list picker and
the sidebar's drag and drop both write here).

Every write returns the full hydrated layout, so the client just swaps it in.
Rows carry the same fields the holdings rail shows: price, D/W/M moves and a
month sparkline (21 closes + spot, the /api/momentum shape). Quotes come from
the shared batched ``prices.quotes`` cache — list names aren't in the holdings
momentum poll.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from portfolio.data import db as db_mod, prices as prices_mod
from portfolio.analytics.cards import _spot_move
from api.auth import current_user_id
from api.serialize import _py

router = APIRouter(prefix="/api", tags=["lists"])

_TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,10}$")
_QUOTE_TTL = 300.0  # 5 min — rail strips, not a trading terminal
_MAX_LISTS = 20
_MAX_ITEMS = 100
_MAX_NAME = 40


def _pct(x: float | None):
    return _py(round(x * 100, 2)) if x is not None else None


def _row(t: str, quote: dict, hist) -> dict:
    try:
        name = prices_mod.profile(t).get("name") or t
    except Exception:
        name = t
    price, prev = quote["price"], quote["prev_close"]
    closes = hist.dropna().tail(21).tolist() if hist is not None else []
    spark = [round(float(v), 2) for v in closes] + ([round(float(price), 2)] if price is not None else [])
    return {
        "ticker": t,
        "name": name,
        "price": _py(round(price, 2)) if price is not None else None,
        "dayPct": _py(round((price / prev - 1) * 100, 2)) if (price and prev) else None,
        "weekPct": _pct(_spot_move(hist, price, 5)),
        "monthPct": _pct(_spot_move(hist, price, 21)),
        "spark": spark,
    }


def _payload(conn, user_id: int) -> list[dict]:
    lists = db_mod.lists_for_user(conn, user_id)
    tickers = sorted({t for L in lists for t in L["tickers"]})
    quotes = prices_mod.quotes(tickers, max_age=_QUOTE_TTL)
    hists = prices_mod.histories(tickers)
    rows = {t: _row(t, quotes[t], hists.get(t)) for t in tickers}
    return [{"id": L["id"], "name": L["name"], "items": [rows[t] for t in L["tickers"]]} for L in lists]


def _ok(conn, user_id: int, error: str | None = None) -> dict:
    return {"ok": error is None, "error": error, "lists": _payload(conn, user_id)}


def _clean_name(name: str | None) -> str | None:
    n = " ".join((name or "").split())
    return n[:_MAX_NAME] if n else None


def _clean_tickers(tickers: list[str]) -> list[str] | None:
    out = [(t or "").strip().upper() for t in tickers]
    if len(out) > _MAX_ITEMS or not all(_TICKER_RE.match(t) for t in out):
        return None
    return list(dict.fromkeys(out))


@router.get("/lists")
def get_lists(user_id: int = Depends(current_user_id)):
    return _payload(db_mod.connect(), user_id)


class ListIn(BaseModel):
    name: str
    tickers: list[str] = []


@router.post("/lists")
def create_list(body: ListIn, user_id: int = Depends(current_user_id)):
    conn = db_mod.connect()
    name = _clean_name(body.name)
    tickers = _clean_tickers(body.tickers)
    if name is None:
        return _ok(conn, user_id, "Name the list.")
    if tickers is None:
        return _ok(conn, user_id, "Invalid ticker.")
    if len(db_mod.lists_for_user(conn, user_id)) >= _MAX_LISTS:
        return _ok(conn, user_id, f"{_MAX_LISTS} lists max.")
    list_id = db_mod.list_create(conn, user_id, name, tickers)
    return {**_ok(conn, user_id), "id": list_id}


class RenameIn(BaseModel):
    name: str


@router.patch("/lists/{list_id}")
def rename_list(list_id: int, body: RenameIn, user_id: int = Depends(current_user_id)):
    conn = db_mod.connect()
    name = _clean_name(body.name)
    if name is None:
        return _ok(conn, user_id, "Name the list.")
    if not db_mod.list_rename(conn, user_id, list_id, name):
        return _ok(conn, user_id, "Unknown list.")
    return _ok(conn, user_id)


@router.delete("/lists/{list_id}")
def delete_list(list_id: int, user_id: int = Depends(current_user_id)):
    conn = db_mod.connect()
    if not db_mod.list_delete(conn, user_id, list_id):
        return _ok(conn, user_id, "Unknown list.")
    return _ok(conn, user_id)


class LayoutList(BaseModel):
    id: int
    tickers: list[str]


class LayoutIn(BaseModel):
    lists: list[LayoutList]


@router.put("/lists")
def set_layout(body: LayoutIn, user_id: int = Depends(current_user_id)):
    """Order of lists + each list's ordered tickers, in one write — every
    sidebar drag (reorder, move between lists, copy a holding in, remove)
    and every list-picker toggle lands here."""
    conn = db_mod.connect()
    layout = []
    for L in body.lists:
        tickers = _clean_tickers(L.tickers)
        if tickers is None:
            return _ok(conn, user_id, "Invalid ticker.")
        layout.append((L.id, tickers))
    if not db_mod.lists_set_layout(conn, user_id, layout):
        return _ok(conn, user_id, "Unknown list.")
    return _ok(conn, user_id)
