"""Shared fixtures for the API test suite.

Every test gets its own throwaway SQLite file (never the real data/portfolio.db)
and a stubbed snapshot so hitting /api/trades or /api/transactions never makes a
live yfinance call — the ledger endpoints only need `open_positions` (for the
"can't sell what you don't hold" check) and `realized` (for GET /api/realized),
so a bare-bones fake snapshot is enough without running the real pipeline.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pandas as pd
import pytest

# Force the auth gate off (no password/secret/OAuth configured) so requests
# resolve to the default user without needing a session cookie — matches how
# `api.auth.current_user_id` behaves in local dev.
for _var in ("SPROUT_PASSWORD", "SPROUT_SECRET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"):
    os.environ.pop(_var, None)

from portfolio.data import db as db_mod  # noqa: E402


def make_fake_snapshot(open_positions: pd.Series | None = None, realized: pd.DataFrame | None = None):
    """A minimal stand-in for PortfolioSnapshot exposing only what the ledger
    router reads — real snapshots run the full analytics pipeline (network I/O),
    which the endpoint tests have no business depending on."""
    return SimpleNamespace(
        open_positions=open_positions if open_positions is not None else pd.Series(dtype=float),
        realized=realized if realized is not None else pd.DataFrame(
            columns=["ticker", "shares", "buy_date", "sell_date", "buy_price", "sell_price", "realized_pnl"]
        ),
    )


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Point the whole app at a fresh, empty SQLite file for this test only."""
    path = tmp_path / "test_portfolio.db"
    monkeypatch.setattr(db_mod, "DEFAULT_DB_PATH", path)
    conn = db_mod.connect(path)
    db_mod.init_schema(conn)
    db_mod.seed_defaults(conn)
    conn.close()
    return path


@pytest.fixture
def other_user_id(db_path) -> int:
    """A second real user (FK-valid) for ownership-scoping tests."""
    conn = db_mod.connect(db_path)
    cur = conn.execute(
        "INSERT INTO users (email, display_name, created_at) VALUES (?, ?, ?)",
        ("friend@example.com", "Friend", "2024-01-01T00:00:00+00:00"),
    )
    conn.commit()
    user_id = int(cur.lastrowid)
    conn.close()
    return user_id


@pytest.fixture
def client(db_path, monkeypatch):
    from api import state

    monkeypatch.setattr(state, "get_snapshot", lambda user_id=db_mod.DEFAULT_USER_ID: make_fake_snapshot())

    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def as_user(client, monkeypatch):
    """Override the request identity for one call — for ownership tests where
    a second user attempts to edit/delete the first user's rows."""

    def _as(user_id: int):
        from api.auth import current_user_id
        from api.main import app

        app.dependency_overrides[current_user_id] = lambda: user_id
        return client

    yield _as
    from api.auth import current_user_id
    from api.main import app

    app.dependency_overrides.pop(current_user_id, None)
