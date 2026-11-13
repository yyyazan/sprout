"""Plan page: the projection's stored inputs plus the Sprout numbers it starts from.

The projection itself runs in the browser (it redraws on every slider move);
this only supplies what the browser can't know: take-home pay and assumptions
(stored per user), today's balance, and what the user has actually been
depositing.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from portfolio.data import db as db_mod
from portfolio.data import loader

from api import state
from api.auth import current_user_id
from api.serialize import _py

router = APIRouter(prefix="/api/plan", tags=["plan"])


def saved_per_month(txn: pd.DataFrame, today: date) -> tuple[float | None, int]:
    """Average net deposit a month over the trailing 12 months.

    Withdrawals count against it. A history shorter than a year is averaged
    over the months it covers (at least one), so a new account isn't read as
    saving a twelfth of what it does. None when nothing was ever deposited.
    """
    if txn.empty:
        return None, 0
    dates = pd.to_datetime(txn["Date"]).dt.date
    start = today - timedelta(days=365)
    recent = txn.loc[dates > start, "Amount (USD)"].astype(float)
    first = max(dates.min(), start)
    months = min(12, max(1, round((today - first).days / 30.44)))
    return float(recent.sum()) / months, months


def _balance(user_id: int) -> float:
    """Portfolio value as the dashboard shows it: holdings at live prices + cash."""
    s = state.get_snapshot(user_id)
    return float(s.pnl["market_value"].sum()) + float(s.free_cash)


def _payload(conn, user_id: int) -> dict:
    settings = db_mod.plan_settings(conn, user_id)
    txn = loader.load_transactions_db(user_id, conn)
    saved, months = saved_per_month(txn, date.today())
    return {
        **{k: _py(v) for k, v in settings.items() if k != "income_steps"},
        "income_steps": settings["income_steps"],
        "balance": _py(_balance(user_id)),
        "saved_monthly": _py(saved),
        "saved_months": months,
    }


@router.get("")
def get_plan(user_id: int = Depends(current_user_id)):
    return _payload(db_mod.connect(), user_id)


Money = Field(ge=0, le=10_000_000)


class IncomeStep(BaseModel):
    """Take-home from `month` on (e.g. a new job after graduating)."""
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    income: float = Money


class PlanIn(BaseModel):
    income_monthly: float | None = Field(default=None, ge=0, le=10_000_000)
    return_pct: float = Field(ge=-20, le=30)
    raise_pct: float = Field(ge=-20, le=30)
    income_steps: list[IncomeStep] = Field(default_factory=list, max_length=12)
    hysa_balance: float = Field(default=0, ge=0, le=10_000_000)
    hysa_apy: float = Field(default=4.0, ge=0, le=20)
    hysa_monthly: float = Field(default=0, ge=0, le=10_000_000)


@router.put("")
def set_plan(body: PlanIn, user_id: int = Depends(current_user_id)):
    settings = body.model_dump()
    settings["income_monthly"] = body.income_monthly or None
    # one income per month, in date order (a later edit of the same month wins)
    by_month = {s["month"]: s["income"] for s in settings["income_steps"]}
    settings["income_steps"] = [{"month": m, "income": by_month[m]} for m in sorted(by_month)]
    conn = db_mod.connect()
    db_mod.update_plan_settings(conn, user_id, settings)
    return _payload(conn, user_id)
