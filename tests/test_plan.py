"""/api/plan: stored projection inputs + the Sprout numbers the page starts from."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from api.routers.plan import saved_per_month
from portfolio.data import db as db_mod


@pytest.fixture
def plan_client(client, monkeypatch):
    from api import state

    snap = SimpleNamespace(pnl=pd.DataFrame({"market_value": [1000.0, 500.0]}), free_cash=250.0)
    monkeypatch.setattr(state, "get_snapshot", lambda user_id=db_mod.DEFAULT_USER_ID: snap)
    return client


def _txn(rows):
    return pd.DataFrame(rows, columns=["Date", "Amount (USD)"]).assign(Date=lambda d: pd.to_datetime(d["Date"]))


def test_defaults_before_anything_is_saved(plan_client):
    body = plan_client.get("/api/plan").json()
    assert body["income_monthly"] is None
    assert body["return_pct"] == 7.0
    assert body["raise_pct"] == 1.0
    assert body["balance"] == 1750.0
    assert body["saved_monthly"] is None


def test_put_round_trips(plan_client):
    r = plan_client.put("/api/plan", json={"income_monthly": 4000, "return_pct": 6, "raise_pct": 2})
    assert r.status_code == 200
    assert r.json()["income_monthly"] == 4000
    body = plan_client.get("/api/plan").json()
    assert (body["income_monthly"], body["return_pct"], body["raise_pct"]) == (4000, 6, 2)


def test_zero_income_clears_it(plan_client):
    plan_client.put("/api/plan", json={"income_monthly": 4000, "return_pct": 7, "raise_pct": 1})
    plan_client.put("/api/plan", json={"income_monthly": 0, "return_pct": 7, "raise_pct": 1})
    assert plan_client.get("/api/plan").json()["income_monthly"] is None


def test_rejects_out_of_range(plan_client):
    r = plan_client.put("/api/plan", json={"income_monthly": -5, "return_pct": 7, "raise_pct": 1})
    assert r.status_code == 422
    r = plan_client.put("/api/plan", json={"income_monthly": 100, "return_pct": 90, "raise_pct": 1})
    assert r.status_code == 422


def test_settings_are_per_user(plan_client, as_user, other_user_id):
    plan_client.put("/api/plan", json={"income_monthly": 4000, "return_pct": 7, "raise_pct": 1})
    assert as_user(other_user_id).get("/api/plan").json()["income_monthly"] is None
    assert as_user(1).get("/api/plan").json()["income_monthly"] == 4000


def test_income_steps_and_hysa_round_trip(plan_client):
    body = {
        "income_monthly": 1500, "return_pct": 7, "raise_pct": 1,
        "income_steps": [{"month": "2028-01", "income": 7000}, {"month": "2027-06", "income": 5500},
                         {"month": "2028-01", "income": 7200}],
        "hysa_balance": 3000, "hysa_apy": 4.2, "hysa_monthly": 200,
    }
    assert plan_client.put("/api/plan", json=body).status_code == 200
    got = plan_client.get("/api/plan").json()
    # sorted by month, one per month, the later duplicate wins
    assert got["income_steps"] == [{"month": "2027-06", "income": 5500}, {"month": "2028-01", "income": 7200}]
    assert (got["hysa_balance"], got["hysa_apy"], got["hysa_monthly"]) == (3000, 4.2, 200)


def test_new_fields_default_when_omitted(plan_client):
    plan_client.put("/api/plan", json={"income_monthly": 4000, "return_pct": 7, "raise_pct": 1})
    got = plan_client.get("/api/plan").json()
    assert got["income_steps"] == [] and got["hysa_balance"] == 0 and got["hysa_apy"] == 4.0


def test_rejects_bad_income_step(plan_client):
    for step in ({"month": "2027-13", "income": 1}, {"month": "June 2027", "income": 1}, {"month": "2027-06", "income": -1}):
        r = plan_client.put("/api/plan", json={"return_pct": 7, "raise_pct": 1, "income_steps": [step]})
        assert r.status_code == 422, step


def test_migration_adds_columns_to_old_table(tmp_path):
    conn = db_mod.connect(tmp_path / "old.db")
    conn.executescript(
        "CREATE TABLE plan_settings (user_id INTEGER PRIMARY KEY, income_monthly REAL, "
        "return_pct REAL NOT NULL DEFAULT 7.0, raise_pct REAL NOT NULL DEFAULT 1.0, updated_at TEXT);"
        "INSERT INTO plan_settings (user_id, income_monthly) VALUES (1, 3000);"
    )
    db_mod.init_schema(conn)
    s = db_mod.plan_settings(conn, 1)
    assert s["income_monthly"] == 3000 and s["income_steps"] == [] and s["hysa_apy"] == 4.0


def test_saved_per_month_trailing_year_counts_withdrawals():
    today = date(2026, 11, 13)
    txn = _txn([
        ("2024-01-01", 9999.0),   # older than a year: ignored
        ("2026-01-10", 600.0),
        ("2026-06-10", 600.0),
        ("2026-09-10", -200.0),
    ])
    saved, months = saved_per_month(txn, today)
    assert months == 12
    assert saved == pytest.approx(1000.0 / 12)


def test_saved_per_month_short_history_uses_months_covered():
    today = date(2026, 11, 13)
    txn = _txn([("2026-08-13", 300.0), ("2026-10-01", 300.0)])
    saved, months = saved_per_month(txn, today)
    assert months == 3
    assert saved == pytest.approx(200.0)


def test_saved_per_month_empty():
    assert saved_per_month(_txn([]), date(2026, 11, 13)) == (None, 0)
