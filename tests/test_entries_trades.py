"""HTTP-level tests for /api/trades — GET/POST/PATCH/DELETE, ownership scoping.

`client` and `as_user` come from conftest.py: the snapshot dependency is
stubbed (no yfinance calls) and every test gets its own throwaway SQLite file.
"""
from __future__ import annotations


def add_trade(client, **overrides):
    body = {"ticker": "AAPL", "action": "buy", "shares": 2, "price": 150.0, "trade_date": "2024-08-20"}
    body.update(overrides)
    return client.post("/api/trades", json=body)


# ── GET ──────────────────────────────────────────────────────────────────────

def test_get_trades_empty(client):
    r = client.get("/api/trades")
    assert r.status_code == 200
    assert r.json() == []


def test_get_trades_returns_id_and_fields(client):
    add_trade(client)
    r = client.get("/api/trades")
    assert r.status_code == 200
    [row] = r.json()
    assert row["ticker"] == "AAPL"
    assert row["action"] == "buy"
    assert row["shares"] == 2
    assert row["price"] == 150.0
    assert row["date"] == "2024-08-20"
    assert isinstance(row["id"], int)


def test_get_trades_sorted_newest_first(client):
    add_trade(client, trade_date="2024-01-01")
    add_trade(client, ticker="MSFT", trade_date="2024-06-01")
    dates = [row["date"] for row in client.get("/api/trades").json()]
    assert dates == ["2024-06-01", "2024-01-01"]


# ── POST (add) ───────────────────────────────────────────────────────────────

def test_add_trade_success(client):
    r = add_trade(client)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["errors"] == {}
    assert len(client.get("/api/trades").json()) == 1


def test_add_trade_validation_error_not_persisted(client):
    r = add_trade(client, ticker="")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "ticker" in body["errors"]
    assert client.get("/api/trades").json() == []


def test_add_sell_without_position_rejected(client):
    r = add_trade(client, action="sell")
    body = r.json()
    assert body["ok"] is False
    assert "ticker" in body["errors"]


def test_add_sell_after_matching_buy_succeeds(client, monkeypatch):
    add_trade(client, action="buy", shares=5)
    # The snapshot stub is static (no live pipeline run), so a sell's "don't
    # exceed what's held" check needs its own snapshot reflecting that buy —
    # this exercises the same wiring a real snapshot would provide.
    import pandas as pd

    from api import state
    from tests.conftest import make_fake_snapshot

    monkeypatch.setattr(
        state, "get_snapshot", lambda user_id=1: make_fake_snapshot(open_positions=pd.Series({"AAPL": 5.0}))
    )
    r = add_trade(client, action="sell", shares=2)
    assert r.json()["ok"] is True
    assert len(client.get("/api/trades").json()) == 2


# ── PATCH (edit) ─────────────────────────────────────────────────────────────

def test_edit_trade_updates_fields(client):
    add_trade(client)
    trade_id = client.get("/api/trades").json()[0]["id"]

    r = client.patch(
        f"/api/trades/{trade_id}",
        json={"ticker": "AAPL", "action": "buy", "shares": 9, "price": 111.0, "trade_date": "2024-09-01"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    [row] = client.get("/api/trades").json()
    assert row["id"] == trade_id
    assert row["shares"] == 9
    assert row["price"] == 111.0
    assert row["date"] == "2024-09-01"


def test_edit_trade_validation_error_leaves_row_unchanged(client):
    add_trade(client)
    trade_id = client.get("/api/trades").json()[0]["id"]

    r = client.patch(
        f"/api/trades/{trade_id}",
        json={"ticker": "AAPL", "action": "buy", "shares": -1, "price": 111.0, "trade_date": "2024-09-01"},
    )
    assert r.json()["ok"] is False
    row = client.get("/api/trades").json()[0]
    assert row["shares"] == 2  # unchanged from add_trade()'s default


def test_edit_nonexistent_trade_returns_not_ok(client):
    r = client.patch(
        "/api/trades/999999",
        json={"ticker": "AAPL", "action": "buy", "shares": 1, "price": 1.0, "trade_date": "2024-01-01"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is False


# ── DELETE ───────────────────────────────────────────────────────────────────

def test_delete_trade(client):
    add_trade(client)
    trade_id = client.get("/api/trades").json()[0]["id"]

    r = client.delete(f"/api/trades/{trade_id}")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert client.get("/api/trades").json() == []


def test_delete_nonexistent_trade_returns_not_ok(client):
    r = client.delete("/api/trades/999999")
    assert r.status_code == 200
    assert r.json()["ok"] is False


# ── ownership scoping ────────────────────────────────────────────────────────

def test_other_user_cannot_edit_trade(client, as_user, other_user_id):
    add_trade(client)  # created as the default user
    trade_id = client.get("/api/trades").json()[0]["id"]

    other_client = as_user(other_user_id)
    r = other_client.patch(
        f"/api/trades/{trade_id}",
        json={"ticker": "AAPL", "action": "buy", "shares": 99, "price": 1.0, "trade_date": "2024-01-01"},
    )
    assert r.json()["ok"] is False

    # untouched when read back as the owning user
    as_user_default = as_user(1)
    row = as_user_default.get("/api/trades").json()[0]
    assert row["shares"] == 2


def test_other_user_cannot_delete_trade(client, as_user, other_user_id):
    add_trade(client)
    trade_id = client.get("/api/trades").json()[0]["id"]

    other_client = as_user(other_user_id)
    r = other_client.delete(f"/api/trades/{trade_id}")
    assert r.json()["ok"] is False

    as_user_default = as_user(1)
    assert len(as_user_default.get("/api/trades").json()) == 1


def test_other_user_has_isolated_trade_list(client, as_user, other_user_id):
    add_trade(client)  # as default user (id=1)

    other_client = as_user(other_user_id)
    assert other_client.get("/api/trades").json() == []

    other_client.post(
        "/api/trades",
        json={"ticker": "TSLA", "action": "buy", "shares": 1, "price": 200.0, "trade_date": "2024-01-01"},
    )
    assert len(other_client.get("/api/trades").json()) == 1

    default_client = as_user(1)
    [row] = default_client.get("/api/trades").json()
    assert row["ticker"] == "AAPL"  # the other user's TSLA trade never shows up here


def test_closed_lists_sold_out_tickers_only(client, monkeypatch):
    import pandas as pd
    from api import state
    from tests.conftest import make_fake_snapshot

    cols = ["ticker", "shares", "buy_date", "sell_date", "buy_price", "sell_price", "realized_pnl"]
    realized = pd.DataFrame(
        [
            ("AAPL", 5.0, "2026-01-02", "2026-02-02", 100.0, 120.0, 100.0),
            ("MSFT", 2.0, "2026-01-02", "2026-03-02", 300.0, 290.0, -20.0),
        ],
        columns=cols,
    )
    monkeypatch.setattr(
        state, "get_snapshot",
        lambda user_id=1: make_fake_snapshot(open_positions=pd.Series({"AAPL": 1.0}), realized=realized),
    )
    rows = client.get("/api/closed").json()
    assert [r["ticker"] for r in rows] == ["MSFT"]
    assert rows[0]["closed"] == "2026-03-02" and rows[0]["realized"] == -20.0
