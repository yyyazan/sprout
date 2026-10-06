"""GET /api/search?q=<query> — ticker/company autocomplete for the add-stock
flow. Wraps yfinance's `Search`, keeps the up-to-8 best EQUITY/ETF matches, and
returns a slim `{symbol, name, exchange, type}` shape for the frontend.

yfinance search is slow and rate-limited, so results are memoised in-process for
5 minutes keyed by the normalised query.
"""
from __future__ import annotations

import time

import yfinance as yf
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["search"])

_SEARCH_TTL = 300.0  # 5 min — yfinance search is slow / rate-limited
_search_cache: dict[str, tuple[float, list[dict]]] = {}

_MAX_RESULTS = 8
_PREFERRED_TYPES = {"EQUITY", "ETF"}


def _quote_to_result(quote: dict) -> dict | None:
    symbol = quote.get("symbol")
    if not symbol:
        return None
    return {
        "symbol": symbol,
        "name": quote.get("shortname") or quote.get("longname") or symbol,
        "exchange": quote.get("exchDisp") or quote.get("exchange") or "",
        "type": quote.get("typeDisp") or quote.get("quoteType") or "",
        # a hint only (the badge's outline); the real classification needs the fund's category
        "kind": "fund" if str(quote.get("quoteType") or "").upper() in {"ETF", "MUTUALFUND"} else "stock",
    }


def _search(query: str) -> list[dict]:
    now = time.time()
    hit = _search_cache.get(query)
    if hit is not None and now - hit[0] < _SEARCH_TTL:
        return hit[1]

    try:
        quotes = yf.Search(query).quotes or []
    except Exception:
        return []  # don't cache transient failures / rate limits

    preferred: list[dict] = []
    fallback: list[dict] = []
    for quote in quotes:
        result = _quote_to_result(quote)
        if result is None:
            continue
        fallback.append(result)
        if str(quote.get("quoteType") or "").upper() in _PREFERRED_TYPES:
            preferred.append(result)

    results = (preferred or fallback)[:_MAX_RESULTS]
    _search_cache[query] = (now, results)
    return results


@router.get("/search")
def search(q: str = ""):
    query = q.strip()
    if not query:
        return {"results": []}
    return {"results": _search(query.lower())}
