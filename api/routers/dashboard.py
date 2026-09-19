from __future__ import annotations

from fastapi import APIRouter, Depends

from portfolio.data import db as db_mod

from api import state
from api.auth import current_user_id
from api.greeting import time_of_day
from api.serialize import dashboard_payload, garden_payload, investments_payload, momentum_payload

router = APIRouter(prefix="/api", tags=["read"])


def _display_name(user_id: int) -> str | None:
    """Name for the greeting, or None to greet without one.

    seed_defaults() names the pre-OAuth user "default" — a placeholder, not a
    person, so it must not reach the header. Google fills in the real name on
    first sign-in.
    """
    conn = db_mod.connect()
    try:
        row = db_mod.user_row(conn, user_id)
    finally:
        conn.close()
    name = row["display_name"] if row else None
    return None if name == "default" else name


@router.get("/dashboard")
def dashboard(user_id: int = Depends(current_user_id)):
    return dashboard_payload(state.get_snapshot(user_id), time_of_day(), _display_name(user_id))


@router.get("/momentum")
def momentum(user_id: int = Depends(current_user_id)):
    """Live intraday momentum, refreshed outside the snapshot cache (short TTL)."""
    return momentum_payload(state.get_snapshot(user_id))


@router.get("/investments")
def investments(user_id: int = Depends(current_user_id)):
    return investments_payload(state.get_snapshot(user_id))


@router.get("/garden")
def garden(user_id: int = Depends(current_user_id)):
    return garden_payload(state.get_snapshot(user_id), time_of_day())
