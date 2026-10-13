"""Market session + extended-hours quote for the stock view's quote line."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from api.routers import stock as stock_router

ET = "America/New_York"


def at(day: str, hhmm: str) -> datetime:
    """An Eastern wall-clock moment as UTC (2026-10-12 is a Monday, EDT)."""
    return pd.Timestamp(f"{day} {hhmm}", tz=ET).to_pydatetime().astimezone(timezone.utc)


def test_session_follows_the_eastern_clock():
    assert stock_router._session_at(at("2026-10-12", "03:59")) == "closed"
    assert stock_router._session_at(at("2026-10-12", "04:00")) == "pre"
    assert stock_router._session_at(at("2026-10-12", "09:30")) == "regular"
    assert stock_router._session_at(at("2026-10-12", "15:59")) == "regular"
    assert stock_router._session_at(at("2026-10-12", "16:00")) == "post"
    assert stock_router._session_at(at("2026-10-12", "20:00")) == "closed"
    assert stock_router._session_at(at("2026-10-10", "12:00")) == "closed"   # Saturday


def bars(*rows):
    idx = pd.DatetimeIndex([pd.Timestamp(t, tz=ET) for t, _ in rows]).tz_convert("UTC")
    return pd.Series([c for _, c in rows], index=idx)


def test_after_hours_quote_is_vs_the_regular_close():
    closes = bars(("2026-10-12 15:59", 100.0), ("2026-10-12 16:30", 101.0), ("2026-10-12 19:58", 102.0))
    ext = stock_router._extended(closes, at("2026-10-12", "20:01"))
    assert ext["label"] == "After hours"
    assert ext["price"] == 102.0 and ext["pct"] == 2.0


def test_pre_market_quote_uses_yesterdays_close():
    closes = bars(("2026-10-09 15:59", 100.0), ("2026-10-12 04:10", 98.0), ("2026-10-12 08:00", 99.0))
    ext = stock_router._extended(closes, at("2026-10-12", "08:01"))
    assert ext["label"] == "Pre-market"
    assert ext["price"] == 99.0 and ext["pct"] == -1.0


def test_no_extended_quote_when_the_last_bar_is_regular():
    closes = bars(("2026-10-12 09:30", 100.0), ("2026-10-12 11:00", 101.0))
    assert stock_router._extended(closes, at("2026-10-12", "11:01")) is None
    assert stock_router._extended(closes.iloc[0:0], at("2026-10-12", "11:01")) is None
