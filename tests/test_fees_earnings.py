"""/api/fees (what held funds cost a year) and the per-user /api/earnings cache."""
from __future__ import annotations

import pytest

from api import state
from api.routers import stock as stock_router
from tests.conftest import make_fake_snapshot


def card(ticker, kind, value):
    return {"ticker": ticker, "kind": kind, "market_value": value, "company_name": ticker, "is_joker": False}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(stock_router, "_info", lambda t: {})
    monkeypatch.setattr(stock_router, "_earnings_cache", {})


def with_cards(monkeypatch, cards):
    snap = make_fake_snapshot()
    snap.cards = cards
    monkeypatch.setattr(state, "get_snapshot", lambda user_id=1: snap)


def test_fees_weigh_each_fund_by_its_value(client, monkeypatch):
    with_cards(monkeypatch, [card("VOO", "index", 10_000), card("ARKK", "fund", 1_000), card("AAPL", "stock", 5_000)])
    monkeypatch.setattr(stock_router, "_fund", lambda t, info: {"expense": {"VOO": 0.0003, "ARKK": 0.0075}[t]})
    body = client.get("/api/fees").json()
    assert body["annual"] == 10.5            # 3.00 + 7.50; the stock costs nothing
    assert body["pct"] == pytest.approx(0.095, abs=1e-3)
    assert [i["ticker"] for i in body["items"]] == ["ARKK", "VOO"]   # costliest first


def test_fees_skip_funds_without_a_published_ratio(client, monkeypatch):
    with_cards(monkeypatch, [card("VOO", "index", 10_000), card("IBIT", "fund", 500)])
    monkeypatch.setattr(stock_router, "_fund", lambda t, info: {"expense": 0.0003 if t == "VOO" else None})
    assert client.get("/api/fees").json()["annual"] == 3.0


def test_fees_are_null_without_funds(client, monkeypatch):
    with_cards(monkeypatch, [card("AAPL", "stock", 5_000)])
    assert client.get("/api/fees").json() == {"annual": None, "pct": None, "items": []}


def test_earnings_cache_is_per_user(client, as_user, other_user_id, monkeypatch):
    held = {1: "AAPL", other_user_id: "NVDA"}

    def snap_for(user_id=1):
        s = make_fake_snapshot()
        s.cards = [card(held[user_id], "stock", 100)]
        return s

    monkeypatch.setattr(state, "get_snapshot", snap_for)
    monkeypatch.setattr(stock_router, "_earnings_date", lambda info: "2999-01-01")

    assert [r["ticker"] for r in client.get("/api/earnings").json()["items"]] == ["AAPL"]
    friend = as_user(other_user_id)
    assert [r["ticker"] for r in friend.get("/api/earnings").json()["items"]] == ["NVDA"]
