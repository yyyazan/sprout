"""GET /api/stock/{ticker} — per-ticker MARKET data for the expanded stock
deep-view: quote, fundamentals, 52-week range, analyst target, and the daily
close line. Position data (shares/cost/value/P&L/weight) stays on the frontend,
which already has it from the dashboard payload.

yfinance `.info` is slow and rate-limited, so it's memoised in-process for 30
minutes. The price line reuses the already-cached prices module.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import yfinance as yf
from fastapi import APIRouter, Query

from portfolio.data import prices as prices_mod
from api.serialize import _py

router = APIRouter(prefix="/api", tags=["stock"])

_INFO_TTL = 1800.0  # 30 min — .info is slow / rate-limited
_info_cache: dict[str, tuple[float, dict]] = {}

_NEWS_TTL = 900.0  # 15 min — headlines churn slowly
_news_cache: dict[str, tuple[float, list]] = {}

_INTRADAY_TTL = 300.0  # 5 min — fine even mid-session for a glance app
_intraday_cache: dict[tuple[str, str], tuple[float, dict]] = {}

_ANALYST_TTL = 1800.0  # ratings move slowly
_analyst_cache: dict[str, tuple[float, dict | None]] = {}

_RELATED_TTL = 1800.0  # Yahoo's similar-symbols list + 4 quotes/sparks
_related_cache: dict[str, tuple[float, list]] = {}


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


def _news(ticker: str, limit: int = 4) -> list[dict]:
    """Top headlines via yfinance `.news`. Handles both the old flat item shape
    and the newer content-nested one; skips anything it can't parse."""
    now = time.time()
    hit = _news_cache.get(ticker)
    if hit is not None and now - hit[0] < _NEWS_TTL:
        return hit[1]
    try:
        items = yf.Ticker(prices_mod.yf_symbol(ticker)).news or []
    except Exception:
        items = []
    out: list[dict] = []
    for it in items:
        try:
            c = it.get("content") or it
            title = c.get("title")
            if not title:
                continue
            url = c.get("link") or it.get("link")
            cu = c.get("canonicalUrl")
            if not url and isinstance(cu, dict):
                url = cu.get("url")
            prov = c.get("provider")
            source = (
                prov.get("displayName") if isinstance(prov, dict) else c.get("publisher")
            ) or ""
            at = None
            ts = it.get("providerPublishTime")
            if ts is not None:
                at = int(ts)
            else:
                pub = c.get("pubDate") or c.get("displayTime")
                if pub:
                    at = int(datetime.fromisoformat(str(pub).replace("Z", "+00:00")).timestamp())
            out.append({"title": str(title), "source": str(source), "url": url, "at": at})
        except Exception:
            continue
        if len(out) >= limit:
            break
    _news_cache[ticker] = (now, out)
    return out


def _analyst(ticker: str, info: dict) -> dict | None:
    """Analyst outlook block: rating buckets (latest month of the
    recommendations trend) + 12-month price targets. None when Yahoo has no
    coverage, so the frontend can skip the section entirely."""
    now = time.time()
    hit = _analyst_cache.get(ticker)
    if hit is not None and now - hit[0] < _ANALYST_TTL:
        return hit[1]

    buckets = None
    try:
        recs = yf.Ticker(prices_mod.yf_symbol(ticker)).recommendations
        if recs is not None and len(recs):
            row = recs.iloc[0]
            buckets = {
                "strongBuy": int(row.get("strongBuy", 0)),
                "buy": int(row.get("buy", 0)),
                "hold": int(row.get("hold", 0)),
                "sell": int(row.get("sell", 0)),
                "strongSell": int(row.get("strongSell", 0)),
            }
    except Exception:
        buckets = None

    target_mean = _py(info.get("targetMeanPrice"))
    out = None
    if buckets and sum(buckets.values()) > 0 or target_mean is not None:
        out = {
            "buckets": buckets,
            "count": _py(info.get("numberOfAnalystOpinions"))
            or (sum(buckets.values()) if buckets else None),
            "verdict": info.get("recommendationKey") or None,
            "targetHigh": _py(info.get("targetHighPrice")),
            "targetLow": _py(info.get("targetLowPrice")),
            "targetMean": target_mean,
        }
    _analyst_cache[ticker] = (now, out)
    return out


@router.get("/stock/{ticker}/related")
def related(ticker: str):
    """Related stocks (Yahoo's similar-symbols list) with a light quote and an
    intraday sparkline each — the GF "Related stocks" row."""
    ticker = ticker.upper()
    now = time.time()
    hit = _related_cache.get(ticker)
    if hit is not None and now - hit[0] < _RELATED_TTL:
        return {"ticker": ticker, "related": hit[1]}

    import requests

    symbols: list[str] = []
    try:
        r = requests.get(
            f"https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/{prices_mod.yf_symbol(ticker)}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        recs = (r.json().get("finance", {}).get("result") or [{}])[0].get("recommendedSymbols") or []
        symbols = [x["symbol"] for x in recs[:4]]
    except Exception:
        symbols = []

    out: list[dict] = []
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            fi = t.fast_info
            price = float(fi.last_price)
            prev = float(fi.previous_close)
            hist = t.history(period="1d", interval="15m")
            spark = [
                _py(round(float(v), 2))
                for v in hist["Close"].dropna().tolist()
            ] if hist is not None and not hist.empty else []
            name = sym
            try:
                name = prices_mod.profile(sym).get("name") or sym
            except Exception:
                pass
            out.append({
                "ticker": sym,
                "name": name,
                "price": _py(round(price, 2)),
                "dayPct": _py(round((price / prev - 1) * 100, 2)) if prev else None,
                "prevClose": _py(round(prev, 2)) if prev else None,
                "spark": spark,
            })
        except Exception:
            continue

    _related_cache[ticker] = (now, out)
    return {"ticker": ticker, "related": out}


def _earnings_date(info: dict) -> str | None:
    """Next earnings date when one is scheduled, else the most recent one.
    `earningsTimestamp` is usually the LAST report; `earningsTimestampStart`
    the upcoming window."""
    stamps = []
    for k in ("earningsTimestamp", "earningsTimestampStart"):
        try:
            v = info.get(k)
            if v is not None:
                stamps.append(int(v))
        except Exception:
            continue
    if not stamps:
        return None
    now = time.time()
    future = [s for s in stamps if s >= now]
    ts = min(future) if future else max(stamps)
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
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
        "earningsDate": _earnings_date(info),
        "analyst": _analyst(ticker, info),
        "news": _news(ticker),
        "history": history,
    }


_MARKET_TTL = 300.0
_market_cache: tuple[float, dict] | None = None

_INDICES = [
    ("SPY", "S&P 500"),
    ("QQQ", "Nasdaq 100"),
    ("BTC-USD", "Bitcoin"),
]


@router.get("/market")
def market():
    """Dashboard market pulse: index quotes + a few market-wide headlines."""
    global _market_cache
    now = time.time()
    if _market_cache is not None and now - _market_cache[0] < _MARKET_TTL:
        return _market_cache[1]
    indices = []
    for sym, label in _INDICES:
        price = day_pct = None
        try:
            fi = yf.Ticker(sym).fast_info
            price = float(fi.last_price)
            prev = float(fi.previous_close)
            if prev:
                day_pct = round((price / prev - 1) * 100, 2)
        except Exception:
            pass
        indices.append({
            "symbol": sym, "label": label,
            "price": _py(round(price, 2)) if price is not None else None,
            "dayPct": _py(day_pct),
        })
    payload = {"indices": indices, "news": _news("^GSPC", limit=3)}
    _market_cache = (now, payload)
    return payload


@router.get("/stock/{ticker}/intraday")
def intraday(ticker: str, rng: str = Query("1d", alias="range")):
    """Intraday bars for the stock view's 1D/1W ranges. 1D = 5-min bars for the
    last session plus the prior session's close (the dotted reference line);
    1W = 30-min bars across the last five sessions."""
    ticker = ticker.upper()
    rng = rng.lower() if rng.lower() in ("1d", "1w") else "1d"
    now = time.time()
    hit = _intraday_cache.get((ticker, rng))
    if hit is not None and now - hit[0] < _INTRADAY_TTL:
        return hit[1]

    points: list[dict] = []
    prev_close = None
    session = None
    try:
        interval = "5m" if rng == "1d" else "30m"
        df = yf.Ticker(prices_mod.yf_symbol(ticker)).history(period="5d", interval=interval)
        if df is not None and not df.empty:
            closes = df["Close"].dropna()
            days = sorted({ts.date() for ts in closes.index})
            if rng == "1d":
                last = days[-1]
                win = closes[[ts.date() == last for ts in closes.index]]
                session = last.strftime("%Y-%m-%d")
                if len(days) > 1:
                    prior = closes[[ts.date() == days[-2] for ts in closes.index]]
                    if not prior.empty:
                        prev_close = _py(round(float(prior.iloc[-1]), 2))
            else:
                win = closes
            points = [
                {"t": int(ts.timestamp()), "c": _py(round(float(v), 2))}
                for ts, v in win.items()
            ]
    except Exception:
        points = []

    if prev_close is None:
        prev_close = _py(_first(_info(ticker), "previousClose", "regularMarketPreviousClose"))

    payload = {"ticker": ticker, "range": rng, "points": points, "prevClose": prev_close, "session": session}
    _intraday_cache[(ticker, rng)] = (now, payload)
    return payload
