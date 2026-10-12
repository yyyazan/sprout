"""/api/market indices carry the same D/W/M moves and month sparkline as the sidebar rows."""
from __future__ import annotations

import pandas as pd
import pytest

from api.routers import stock as stock_router
from portfolio.data import prices as prices_mod


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(stock_router, "_market_cache", None)
    monkeypatch.setattr(stock_router, "_news", lambda *a, **k: [])
    monkeypatch.setattr(prices_mod, "quotes", lambda ts, max_age=0: {t: {"price": 110.0, "prev_close": 100.0} for t in ts})
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize() - pd.Timedelta(days=1), periods=30)
    monkeypatch.setattr(prices_mod, "histories", lambda ts: {t: pd.Series(100.0, index=idx) for t in ts})


def test_indices_have_day_week_month_and_spark(client):
    body = client.get("/api/market").json()
    assert [i["symbol"] for i in body["indices"]] == ["SPY", "QQQ", "BTC-USD"]
    spy = body["indices"][0]
    assert (spy["dayPct"], spy["weekPct"], spy["monthPct"]) == (10.0, 10.0, 10.0)
    assert len(spy["spark"]) == 22            # 21 closes + spot
    assert spy["spark"][-1] == 110.0


def test_missing_history_leaves_moves_blank_not_broken(client, monkeypatch):
    monkeypatch.setattr(prices_mod, "histories", lambda ts: {t: pd.Series(dtype=float) for t in ts})
    spy = client.get("/api/market").json()["indices"][0]
    assert spy["dayPct"] == 10.0              # day move comes from the quote, not history
    assert spy["weekPct"] is None and spy["monthPct"] is None
    assert spy["spark"] == [110.0]
