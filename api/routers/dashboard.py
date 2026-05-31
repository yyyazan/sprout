from __future__ import annotations

from fastapi import APIRouter

from portfolio.data import db as db_mod

from api import state
from api.greeting import time_of_day
from api.serialize import dashboard_payload, garden_payload, investments_payload, momentum_payload

router = APIRouter(prefix="/api", tags=["read"])


@router.get("/dashboard")
def dashboard(user_id: int = db_mod.DEFAULT_USER_ID):
    return dashboard_payload(state.get_snapshot(user_id), time_of_day())


@router.get("/momentum")
def momentum(user_id: int = db_mod.DEFAULT_USER_ID):
    """Live intraday momentum, refreshed outside the snapshot cache (short TTL)."""
    return momentum_payload(state.get_snapshot(user_id))


@router.get("/investments")
def investments(user_id: int = db_mod.DEFAULT_USER_ID):
    return investments_payload(state.get_snapshot(user_id))


@router.get("/garden")
def garden(user_id: int = db_mod.DEFAULT_USER_ID):
    return garden_payload(state.get_snapshot(user_id), time_of_day())
