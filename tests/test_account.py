"""HTTP-level tests for /api/account/reconciliation."""
from __future__ import annotations


def test_get_reconciliation_defaults_to_seeded_zero(client):
    r = client.get("/api/account/reconciliation")
    assert r.status_code == 200
    body = r.json()
    assert body["offset_usd"] == 0.0
    assert body["note"] is not None  # seed_defaults() leaves an explanatory note


def test_set_reconciliation_updates_offset_and_note(client):
    r = client.patch("/api/account/reconciliation", json={"offset_usd": 42.5, "note": "bank fee catch-up"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["offset_usd"] == 42.5
    assert body["note"] == "bank fee catch-up"
    assert body["reconciled_at"]  # timestamp was set

    r2 = client.get("/api/account/reconciliation")
    assert r2.json()["offset_usd"] == 42.5


def test_set_reconciliation_accepts_negative_offset(client):
    r = client.patch("/api/account/reconciliation", json={"offset_usd": -13.37})
    assert r.json()["offset_usd"] == -13.37


def test_set_reconciliation_blank_note_becomes_null(client):
    r = client.patch("/api/account/reconciliation", json={"offset_usd": 1.0, "note": "   "})
    assert r.json()["note"] is None


def test_reconciliation_is_isolated_per_user(client, as_user, other_user_id):
    client.patch("/api/account/reconciliation", json={"offset_usd": 100.0, "note": "owner's offset"})

    other_client = as_user(other_user_id)
    other_r = other_client.get("/api/account/reconciliation")
    # a brand-new user gets their own seeded row via find_or_create_user in
    # real usage, but this fixture only inserts a bare `users` row — reading
    # it back should not somehow see the default user's value
    assert other_r.json()["offset_usd"] != 100.0

    other_client.patch("/api/account/reconciliation", json={"offset_usd": -5.0, "note": "friend's offset"})
    default_client = as_user(1)
    assert default_client.get("/api/account/reconciliation").json()["offset_usd"] == 100.0
