"""Ledger: trade/transaction/realized reads + the two write endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

import pandas as pd

from portfolio.data import db as db_mod, loader, prices, writer

from api import state
from api.serialize import _py, realized_payload
from api.validation import validate_trade, validate_txn

router = APIRouter(prefix="/api", tags=["ledger"])


def _direction(amount: float) -> str:
    return "Deposit" if amount >= 0 else "Withdrawal"


@router.get("/trades")
def trades(user_id: int = db_mod.DEFAULT_USER_ID):
    conn = db_mod.connect()
    df = loader.load_trades_db(user_id, conn).sort_values("date", ascending=False)
    return [
        {
            "ticker": str(t),
            "action": str(a),
            "shares": _py(sh),
            "price": _py(px),
            "date": pd_ts.strftime("%Y-%m-%d"),
        }
        for t, a, sh, px, pd_ts in zip(
            df["ticker"], df["action"], df["shares"], df["price"], df["date"]
        )
    ]


@router.get("/transactions")
def transactions(user_id: int = db_mod.DEFAULT_USER_ID):
    conn = db_mod.connect()
    df = loader.load_transactions_db(user_id, conn).sort_values("Date", ascending=False)
    return [
        {
            "date": d.strftime("%Y-%m-%d"),
            "amount": _py(amt),
            "direction": _direction(float(amt)),
        }
        for d, amt in zip(df["Date"], df["Amount (USD)"])
    ]


@router.get("/realized")
def realized(user_id: int = db_mod.DEFAULT_USER_ID):
    return realized_payload(state.get_snapshot(user_id))


class TradeIn(BaseModel):
    ticker: str
    action: str
    shares: float | None = None
    price: float | None = None  # per-share execution price; None → closing price
    trade_date: str


class TxnIn(BaseModel):
    txn_date: str
    txn_type: str
    amount: float | None = None


@router.post("/trades")
def add_trade(body: TradeIn, user_id: int = db_mod.DEFAULT_USER_ID):
    snap = state.get_snapshot(user_id)
    errors, clean = validate_trade(
        body.ticker, body.action, body.shares, body.trade_date, body.price, snapshot=snap
    )
    if errors:
        return {"ok": False, "errors": errors}
    price = clean["price"]
    if price is None:
        # No price entered → record the close on the trade date (same convention
        # as the backfill of pre-price trades).
        price = prices.price_on_date(clean["ticker"], pd.Timestamp(clean["trade_date"]))
    conn = db_mod.connect()
    writer.insert_trade_db(
        user_id,
        conn,
        ticker=clean["ticker"],
        action=clean["action"],
        shares=clean["shares"],
        trade_date=clean["trade_date"],
        price=price,
    )
    state.invalidate(user_id)
    return {"ok": True, "errors": {}}


@router.post("/transactions")
def add_transaction(body: TxnIn, user_id: int = db_mod.DEFAULT_USER_ID):
    error, clean = validate_txn(body.txn_date, body.txn_type, body.amount)
    if error:
        return {"ok": False, "error": error}
    conn = db_mod.connect()
    writer.insert_transaction_db(
        user_id, conn, txn_date=clean["txn_date"], amount=clean["amount"]
    )
    state.invalidate(user_id)
    return {"ok": True, "error": None}
