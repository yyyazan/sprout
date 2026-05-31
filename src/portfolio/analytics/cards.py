"""Card-hand data — turn open positions into playing cards.

Each open position becomes a card whose *rank* is its risk-adjusted 90-day
performance percentile (Ace best, 2 worst) and whose *suit* is its sector. A
final Joker card carries free cash. The dicts here are consumed verbatim by
`app/components/cards/card_hand.py`; no P&L/return lives on the card *face*
(only inside the hover-reveal detail).

Everything yfinance-touching (sector/name via `prices.profile`, prices) is
already process-cached, and this runs once at boot inside the pipeline, so the
card data is computed without paying network latency on render.
"""
from __future__ import annotations

import pandas as pd

from portfolio.data import prices as prices_mod

# Rank ladder, worst → best. 12 ranks; positions map linearly onto it.
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "J", "Q", "K", "A"]

# Sector → suit. Default unrecognised/empty sectors to diamonds.
SUIT_OF_SECTOR = {
    "Technology": "sp",
    "Communication Services": "sp",
    "Consumer Cyclical": "ht",
    "Consumer Discretionary": "ht",
    "Consumer Defensive": "ht",
    "Consumer Staples": "ht",
    "Healthcare": "dm",
    "Financial Services": "dm",
    "Financials": "dm",
    "Utilities": "dm",
    "Real Estate": "dm",
    "Energy": "cl",
    "Basic Materials": "cl",
    "Materials": "cl",
    "Industrials": "cl",
}
SUIT_SYMBOL = {"sp": "♠", "ht": "♥", "dm": "♦", "cl": "♣", "jk": ""}

TICKER_DOMAINS = {
    "AAPL": "apple.com", "NVDA": "nvidia.com", "GOOG": "abc.xyz",
    "TSLA": "tesla.com", "AMZN": "amazon.com", "MSFT": "microsoft.com",
    "SNOW": "snowflake.com", "RKLB": "rocketlabusa.com", "RGTI": "rigetti.com",
    "RDDT": "reddit.com", "IONQ": "ionq.com", "IBIT": "ishares.com",
    "UNH": "unitedhealthgroup.com", "VSCO": "victoriassecret.com",
    "VOO": "vanguard.com",
}

_WINDOW = 90  # trading days for the rank lookback


def _value_on_or_before(series: pd.Series, date: pd.Timestamp) -> float | None:
    if series is None or series.empty:
        return None
    valid = series[series.index <= date]
    return float(valid.iloc[-1]) if not valid.empty else None


def _trailing_return(series: pd.Series, window: int = _WINDOW) -> float | None:
    """Simple return over the last `window` trading rows (decimal)."""
    s = series.dropna() if series is not None else pd.Series(dtype=float)
    if len(s) < 2:
        return None
    w = s.iloc[-(window + 1):]
    start = float(w.iloc[0])
    if start == 0:
        return None
    return float(w.iloc[-1]) / start - 1.0


def _trailing_vol(series: pd.Series, window: int = _WINDOW) -> float | None:
    """Std of daily returns over the last `window` trading rows."""
    s = series.dropna() if series is not None else pd.Series(dtype=float)
    if len(s) < 3:
        return None
    rets = s.pct_change().dropna().iloc[-window:]
    vol = float(rets.std())
    return vol if vol and vol > 0 else None


def _spot_move(series: pd.Series, spot_price: float | None, sessions: int) -> float | None:
    """Intraday % move (decimal): live spot vs the close `sessions` *completed*
    trading days ago. sessions=1 → today so far, sessions=5 → this week so far.

    Today's own (possibly intraday) history row is dropped so we never compare
    spot against itself. Returns None if spot or history is missing.
    """
    if spot_price is None or series is None:
        return None
    s = series.dropna()
    if s.empty:
        return None
    try:
        today = pd.Timestamp.today().normalize()
        completed = s[s.index.normalize() < today]
    except Exception:
        completed = s
    if completed.empty:
        completed = s
    if len(completed) < sessions:
        return None
    ref = float(completed.iloc[-sessions])
    if ref == 0:
        return None
    return spot_price / ref - 1.0


def compute_ranks(
    tickers: list[str],
    histories: dict[str, pd.Series],
    spy_hist: pd.Series,
) -> dict[str, str]:
    """Map each ticker to a rank by risk-adjusted 90-day excess return vs SPY.

    score = (ticker 90d return − SPY 90d return) / ticker 90d volatility.
    Highest score → Ace, lowest → 2, linear across the ladder. Tickers we
    can't score fall to the worst rank ('2').
    """
    if not tickers:
        return {}

    spy_ret = _trailing_return(spy_hist) or 0.0
    scores: dict[str, float] = {}
    for t in tickers:
        ret = _trailing_return(histories.get(t))
        vol = _trailing_vol(histories.get(t))
        if ret is None or vol is None:
            scores[t] = float("-inf")  # unrankable → worst
        else:
            scores[t] = (ret - spy_ret) / vol

    ordered = sorted(tickers, key=lambda t: scores[t])  # ascending: worst first
    n = len(ordered)
    out: dict[str, str] = {}
    for i, t in enumerate(ordered):
        if scores[t] == float("-inf"):
            out[t] = RANKS[0]
            continue
        idx = 0 if n == 1 else round(i / (n - 1) * (len(RANKS) - 1))
        out[t] = RANKS[idx]
    return out


def _suit_for(ticker: str) -> str:
    sector = prices_mod.profile(ticker).get("sector", "")
    return SUIT_OF_SECTOR.get(sector, "dm")


def compute_positions(
    pnl: pd.DataFrame,
    trades_adj: pd.DataFrame,
    histories: dict[str, pd.Series],
    spy_hist: pd.Series,
    voo_hist: pd.Series,
    free_cash: float,
) -> list[dict]:
    """Build the ordered list of position dicts (positions first, Joker last).

    Neutral position data shared by both the card hand and the garden view;
    ``rank`` and ``suit`` are position attributes, not card concepts.
    """
    tickers = list(pnl.index)
    total_mv = float(pnl["market_value"].sum()) or 0.0
    ranks = compute_ranks(tickers, histories, spy_hist)

    today = pd.Timestamp.today().normalize()
    voo_now = float(voo_hist.iloc[-1]) if (voo_hist is not None and not voo_hist.empty) else None

    buys = trades_adj[trades_adj["action"] == "buy"]
    first_buy = buys.groupby("ticker")["date"].min()

    cards: list[dict] = []
    for t in tickers:
        row = pnl.loc[t]
        try:
            suit = _suit_for(t)
        except Exception:
            suit = "dm"
        try:
            name = prices_mod.profile(t).get("name", "") or t
        except Exception:
            name = t

        entry = first_buy.get(t)
        hold_days = int((today - entry).days) if entry is not None and pd.notna(entry) else 0

        # vs VOO since entry: position return − VOO return over the same window.
        voo_delta_pp = 0.0
        try:
            voo_entry = _value_on_or_before(voo_hist, entry) if entry is not None else None
            if voo_now is not None and voo_entry:
                voo_ret_pp = (voo_now / voo_entry - 1.0) * 100.0
                voo_delta_pp = round(float(row["return_pct"]) - voo_ret_pp, 1)
        except Exception:
            voo_delta_pp = 0.0

        mv = float(row["market_value"])

        # Momentum: INTRADAY % move = live spot price vs the close N completed
        # trading days ago (1 = today so far, 5 = this week). Uses prices.spot()
        # so a mid-session check reflects right-now, not last night's close.
        # Non-deterministic + one live call per holding; None if spot/history missing.
        hist = histories.get(t)
        try:
            spot_price = prices_mod.spot(t)
        except Exception:
            spot_price = None
        day_ret = _spot_move(hist, spot_price, 1)
        week_ret = _spot_move(hist, spot_price, 5)

        cards.append({
            "ticker": t,
            "company_name": name,
            "domain": TICKER_DOMAINS.get(t, ""),
            "suit": suit,
            "suit_symbol": SUIT_SYMBOL.get(suit, "♦"),
            "rank": ranks.get(t, "2"),
            "position_pct": round(mv / total_mv * 100, 1) if total_mv else 0.0,
            "day_pct": round(day_ret * 100, 2) if day_ret is not None else None,
            "week_pct": round(week_ret * 100, 2) if week_ret is not None else None,
            "current_price": round(float(row["current_price"]), 2),
            "shares": round(float(row["shares"]), 2),
            "market_value": round(mv, 2),
            "cost_basis": round(float(row["cost_basis"]), 2),
            "hold_days": hold_days,
            "voo_delta_pp": voo_delta_pp,
            "is_joker": False,
            "cash_usd": 0.0,
        })

    # Joker — free cash. No rank, no suit.
    cards.append({
        "ticker": "CASH",
        "company_name": "Free Cash",
        "domain": "",
        "suit": "jk",
        "suit_symbol": "",
        "rank": "★",
        "position_pct": 0.0,
        "day_pct": None,
        "week_pct": None,
        "current_price": 0.0,
        "shares": 0.0,
        "market_value": 0.0,
        "cost_basis": 0.0,
        "hold_days": 0,
        "voo_delta_pp": 0.0,
        "is_joker": True,
        "cash_usd": round(float(free_cash), 2),
    })
    return cards
