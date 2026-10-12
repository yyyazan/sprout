"""Sign-in is Google only. There is no password path, and a leftover
SPROUT_PASSWORD (the old owner fallback) must be inert: not a login, not a gate,
not a session-signing key."""
from __future__ import annotations

import hashlib
import hmac
import time

import pytest

from api import auth


@pytest.fixture
def gate_on(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("SPROUT_SECRET", "test-signing-key")


def cookie(token: str) -> dict:
    return {"Cookie": f"{auth.COOKIE_NAME}={token}"}


def test_api_is_locked_without_a_session(client, gate_on):
    assert client.get("/api/trades").status_code == 401


def test_a_real_session_gets_through(client, gate_on):
    assert client.get("/api/trades", headers=cookie(auth._make_token(1))).status_code == 200


def test_password_login_route_is_gone(client, gate_on, monkeypatch):
    monkeypatch.setenv("SPROUT_PASSWORD", "123")  # a variable left over on the host
    r = client.post("/api/auth/login", json={"password": "123"})
    assert r.status_code in (404, 405)
    assert auth.COOKIE_NAME not in r.headers.get("set-cookie", "")
    assert client.get("/api/trades").status_code == 401


def test_password_alone_does_not_turn_the_gate_on(client, monkeypatch):
    monkeypatch.setenv("SPROUT_PASSWORD", "123")
    assert auth.enabled() is False


def test_old_password_cannot_sign_a_session(client, gate_on, monkeypatch):
    # The fallback used to double as the signing key when SPROUT_SECRET was unset,
    # so a cookie MACed with it must no longer verify.
    monkeypatch.delenv("SPROUT_SECRET")
    monkeypatch.setenv("SPROUT_PASSWORD", "123")
    payload = f"1.{int(time.time())}"
    forged = f"{payload}.{hmac.new(b'123', payload.encode(), hashlib.sha256).hexdigest()}"
    assert client.get("/api/trades", headers=cookie(forged)).status_code == 401
