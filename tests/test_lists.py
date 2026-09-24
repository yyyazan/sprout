"""HTTP-level tests for /api/lists and the watchlist → lists migration."""
from __future__ import annotations

import pandas as pd
import pytest

from portfolio.data import db as db_mod, prices as prices_mod


@pytest.fixture(autouse=True)
def no_market(monkeypatch):
    """Lists hydrate rows with quotes/history/profile — stub them offline."""
    monkeypatch.setattr(prices_mod, "quotes", lambda ts, max_age=0: {t: {"price": 110.0, "prev_close": 100.0} for t in ts})
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize() - pd.Timedelta(days=1), periods=30)
    monkeypatch.setattr(prices_mod, "histories", lambda ts: {t: pd.Series(100.0, index=idx) for t in ts})
    monkeypatch.setattr(prices_mod, "profile", lambda t: {"name": f"{t} Inc."})


def tickers(lists):
    return {L["name"]: [i["ticker"] for i in L["items"]] for L in lists}


def test_create_and_read_back(client):
    r = client.post("/api/lists", json={"name": "  Tech   names ", "tickers": ["nvda", "AAPL", "NVDA"]})
    body = r.json()
    assert body["ok"] is True
    assert tickers(body["lists"]) == {"Tech names": ["NVDA", "AAPL"]}
    row = body["lists"][0]["items"][0]
    assert row["name"] == "NVDA Inc."
    assert row["dayPct"] == 10.0
    assert row["spark"][-1] == 110.0
    assert client.get("/api/lists").json()[0]["id"] == body["id"]


def test_create_rejects_blank_name_and_bad_ticker(client):
    assert client.post("/api/lists", json={"name": "   "}).json()["ok"] is False
    assert client.post("/api/lists", json={"name": "x", "tickers": ["NOT A TICKER"]}).json()["ok"] is False
    assert client.get("/api/lists").json() == []


def test_layout_reorders_lists_and_moves_items(client):
    a = client.post("/api/lists", json={"name": "A", "tickers": ["AAPL", "MSFT"]}).json()["id"]
    b = client.post("/api/lists", json={"name": "B", "tickers": ["TSLA"]}).json()["id"]
    r = client.put("/api/lists", json={"lists": [
        {"id": b, "tickers": ["TSLA", "MSFT"]},
        {"id": a, "tickers": ["AAPL"]},
    ]}).json()
    assert r["ok"] is True
    assert [L["name"] for L in r["lists"]] == ["B", "A"]
    assert tickers(r["lists"]) == {"B": ["TSLA", "MSFT"], "A": ["AAPL"]}


def test_partial_layout_keeps_other_lists(client):
    a = client.post("/api/lists", json={"name": "A", "tickers": ["AAPL"]}).json()["id"]
    b = client.post("/api/lists", json={"name": "B", "tickers": ["TSLA"]}).json()["id"]
    r = client.put("/api/lists", json={"lists": [{"id": b, "tickers": []}]}).json()
    assert [L["name"] for L in r["lists"]] == ["B", "A"]
    assert tickers(r["lists"]) == {"B": [], "A": ["AAPL"]}
    assert a


def test_rename_and_delete(client):
    lid = client.post("/api/lists", json={"name": "Old"}).json()["id"]
    assert client.patch(f"/api/lists/{lid}", json={"name": "New"}).json()["lists"][0]["name"] == "New"
    assert client.delete(f"/api/lists/{lid}").json()["lists"] == []


def test_lists_are_isolated_per_user(client, as_user, other_user_id):
    mine = client.post("/api/lists", json={"name": "Mine", "tickers": ["AAPL"]}).json()["id"]

    other = as_user(other_user_id)
    assert other.get("/api/lists").json() == []
    assert other.patch(f"/api/lists/{mine}", json={"name": "Hijacked"}).json()["ok"] is False
    assert other.delete(f"/api/lists/{mine}").json()["ok"] is False
    assert other.put("/api/lists", json={"lists": [{"id": mine, "tickers": []}]}).json()["ok"] is False

    owner = as_user(db_mod.DEFAULT_USER_ID)
    assert tickers(owner.get("/api/lists").json()) == {"Mine": ["AAPL"]}


def test_watchlist_migrates_once(tmp_path):
    conn = db_mod.connect(tmp_path / "legacy.db")
    conn.executescript(
        """
        CREATE TABLE users (user_id INTEGER PRIMARY KEY, email TEXT, display_name TEXT, created_at TEXT NOT NULL);
        INSERT INTO users VALUES (1, NULL, 'default', '2024-01-01');
        CREATE TABLE watchlist (user_id INTEGER NOT NULL, ticker TEXT NOT NULL, added_at TEXT NOT NULL,
                                PRIMARY KEY (user_id, ticker));
        INSERT INTO watchlist VALUES (1, 'TSLA', '2024-02-01'), (1, 'AAPL', '2024-01-01');
        """
    )
    db_mod.init_schema(conn)
    assert db_mod.lists_for_user(conn, 1) == [{"id": 1, "name": "Watchlist", "tickers": ["AAPL", "TSLA"]}]

    db_mod.list_delete(conn, 1, 1)
    db_mod.init_schema(conn)  # a restart must not resurrect it
    assert db_mod.lists_for_user(conn, 1) == []
    assert conn.execute("SELECT COUNT(*) FROM watchlist_legacy").fetchone()[0] == 2
