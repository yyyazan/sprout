"""Account-level settings — currently just cash reconciliation.

Previously the only way to set a user's cash offset was a direct SQLite edit;
this is the first real write path for it.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from portfolio.data import db as db_mod

from api import state
from api.auth import current_user_id
from api.serialize import _py

router = APIRouter(prefix="/api/account", tags=["account"])


def _payload(conn, user_id: int) -> dict:
    row = db_mod.reconciliation_row(conn, user_id)
    if row is None:
        return {"offset_usd": 0.0, "reconciled_at": None, "note": None}
    return {
        "offset_usd": _py(row["offset_usd"]),
        "reconciled_at": row["reconciled_at"],
        "note": row["note"],
    }


@router.get("/reconciliation")
def get_reconciliation(user_id: int = Depends(current_user_id)):
    return _payload(db_mod.connect(), user_id)


class ReconciliationIn(BaseModel):
    offset_usd: float
    note: str | None = None


@router.patch("/reconciliation")
def set_reconciliation(body: ReconciliationIn, user_id: int = Depends(current_user_id)):
    note = (body.note or "").strip() or None
    conn = db_mod.connect()
    db_mod.update_reconciliation(conn, user_id, body.offset_usd, note)
    state.invalidate(user_id)  # free_cash / cash_ts bake the offset in at compute time
    return {"ok": True, **_payload(conn, user_id)}
