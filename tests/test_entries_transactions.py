"""HTTP-level tests for /api/transactions — GET/POST/PATCH/DELETE, ownership
scoping. Unlike trades, transaction validation never touches the snapshot, so
these don't need any snapshot-related setup beyond what conftest already stubs.
"""
from __future__ import annotations


def add_txn(client, **overrides):
    body = {"txn_date": "2024-08-20", "txn_type": "Deposit", "amount": 100.0}
    body.update(overrides)
    return client.post("/api/transactions", json=body)


# ── GET ──────────────────────────────────────────────────────────────────────

def test_get_transactions_empty(client):
    assert client.get("/api/transactions").json() == []


def test_get_transactions_returns_id_and_signed_amount(client):
    add_txn(client)
    [row] = client.get("/api/transactions").json()
    assert row["date"] == "2024-08-20"
    assert row["amount"] == 100.0
    assert row["direction"] == "Deposit"
    assert isinstance(row["id"], int)


def test_withdrawal_amount_is_negative(client):
    add_txn(client, txn_type="Withdrawal", amount=40)
    [row] = client.get("/api/transactions").json()
    assert row["amount"] == -40
    assert row["direction"] == "Withdrawal"


def test_get_transactions_sorted_newest_first(client):
    add_txn(client, txn_date="2024-01-01")
    add_txn(client, txn_date="2024-06-01")
    dates = [row["date"] for row in client.get("/api/transactions").json()]
    assert dates == ["2024-06-01", "2024-01-01"]


# ── POST (add) ───────────────────────────────────────────────────────────────

def test_add_transaction_success(client):
    r = add_txn(client)
    assert r.status_code == 200
    assert r.json() == {"ok": True, "error": None}
    assert len(client.get("/api/transactions").json()) == 1


def test_add_transaction_validation_error_not_persisted(client):
    r = add_txn(client, amount=-5)
    assert r.json()["ok"] is False
    assert r.json()["error"]
    assert client.get("/api/transactions").json() == []


def test_add_transaction_rejects_bad_type(client):
    r = add_txn(client, txn_type="Transfer")
    assert r.json()["ok"] is False


# ── PATCH (edit) ─────────────────────────────────────────────────────────────

def test_edit_transaction_updates_fields(client):
    add_txn(client)
    txn_id = client.get("/api/transactions").json()[0]["id"]

    r = client.patch(f"/api/transactions/{txn_id}", json={"txn_date": "2024-09-01", "txn_type": "Withdrawal", "amount": 25})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "error": None}

    [row] = client.get("/api/transactions").json()
    assert row["id"] == txn_id
    assert row["date"] == "2024-09-01"
    assert row["amount"] == -25
    assert row["direction"] == "Withdrawal"


def test_edit_transaction_validation_error_leaves_row_unchanged(client):
    add_txn(client)
    txn_id = client.get("/api/transactions").json()[0]["id"]

    r = client.patch(f"/api/transactions/{txn_id}", json={"txn_date": "2024-09-01", "txn_type": "Deposit", "amount": -1})
    assert r.json()["ok"] is False
    row = client.get("/api/transactions").json()[0]
    assert row["amount"] == 100.0  # unchanged


def test_edit_nonexistent_transaction_returns_not_ok(client):
    r = client.patch("/api/transactions/999999", json={"txn_date": "2024-01-01", "txn_type": "Deposit", "amount": 1})
    assert r.status_code == 200
    assert r.json()["ok"] is False


# ── DELETE ───────────────────────────────────────────────────────────────────

def test_delete_transaction(client):
    add_txn(client)
    txn_id = client.get("/api/transactions").json()[0]["id"]

    r = client.delete(f"/api/transactions/{txn_id}")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "error": None}
    assert client.get("/api/transactions").json() == []


def test_delete_nonexistent_transaction_returns_not_ok(client):
    r = client.delete("/api/transactions/999999")
    assert r.status_code == 200
    assert r.json()["ok"] is False


# ── ownership scoping ────────────────────────────────────────────────────────

def test_other_user_cannot_edit_transaction(client, as_user, other_user_id):
    add_txn(client)  # created as the default user
    txn_id = client.get("/api/transactions").json()[0]["id"]

    other_client = as_user(other_user_id)
    r = other_client.patch(f"/api/transactions/{txn_id}", json={"txn_date": "2024-01-01", "txn_type": "Deposit", "amount": 9999})
    assert r.json()["ok"] is False

    default_client = as_user(1)
    row = default_client.get("/api/transactions").json()[0]
    assert row["amount"] == 100.0


def test_other_user_cannot_delete_transaction(client, as_user, other_user_id):
    add_txn(client)
    txn_id = client.get("/api/transactions").json()[0]["id"]

    other_client = as_user(other_user_id)
    r = other_client.delete(f"/api/transactions/{txn_id}")
    assert r.json()["ok"] is False

    default_client = as_user(1)
    assert len(default_client.get("/api/transactions").json()) == 1


def test_other_user_has_isolated_transaction_list(client, as_user, other_user_id):
    add_txn(client)  # as default user

    other_client = as_user(other_user_id)
    assert other_client.get("/api/transactions").json() == []

    other_client.post("/api/transactions", json={"txn_date": "2024-02-02", "txn_type": "Withdrawal", "amount": 10})
    assert len(other_client.get("/api/transactions").json()) == 1

    default_client = as_user(1)
    [row] = default_client.get("/api/transactions").json()
    assert row["direction"] == "Deposit"  # the other user's withdrawal never shows up here
