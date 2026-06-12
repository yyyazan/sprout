"""Trade/transaction validation — moved verbatim from app/pages/trades.py.

Pure functions, no web framework. `validate_trade` takes the user's snapshot
explicitly (instead of importing a global get_snapshot) so it stays decoupled.
"""
from __future__ import annotations

import re
from datetime import date, datetime

TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
TXN_TYPES = ["Deposit", "Withdrawal"]


def parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def validate_trade(
    ticker, action, shares, trade_date, price=None, *, snapshot
) -> tuple[dict[str, str], dict]:
    errors: dict[str, str] = {}

    cleaned_ticker = str(ticker or "").strip().upper()
    if not cleaned_ticker:
        errors["ticker"] = "Required."
    elif not TICKER_RE.match(cleaned_ticker):
        errors["ticker"] = "Invalid format."

    if action not in {"buy", "sell"}:
        errors["action"] = "Pick Buy or Sell."

    try:
        shares_val = float(shares) if shares not in (None, "") else None
    except (TypeError, ValueError):
        shares_val = None
    if shares_val is None:
        errors["shares"] = "Required."
    elif shares_val <= 0:
        errors["shares"] = "Must be > 0."

    # Execution price is optional — blank means "use the closing price".
    try:
        price_val = float(price) if price not in (None, "") else None
    except (TypeError, ValueError):
        price_val = None
        errors["price"] = "Must be a number."
    if price_val is not None and price_val <= 0:
        errors["price"] = "Must be > 0."

    parsed = parse_date(trade_date)
    if parsed is None:
        errors["date"] = "Invalid date."
    elif parsed > date.today():
        errors["date"] = "Cannot be future."

    if not errors and action == "sell":
        held = (
            float(snapshot.open_positions.get(cleaned_ticker, 0.0))
            if cleaned_ticker in snapshot.open_positions.index
            else 0.0
        )
        if held <= 0:
            errors["ticker"] = f"No open position in {cleaned_ticker}."
        elif shares_val > held + 1e-6:
            errors["shares"] = f"Exceeds {held:.4f} held."

    if errors:
        return errors, {}
    return {}, {
        "ticker": cleaned_ticker,
        "action": action,
        "shares": shares_val,
        "trade_date": parsed,
        "price": price_val,
    }


def validate_txn(txn_date, txn_type, amount) -> tuple[str | None, dict]:
    parsed = parse_date(txn_date)
    if parsed is None:
        return "Date is invalid.", {}
    if parsed > date.today():
        return "Date cannot be in the future.", {}
    if txn_type not in TXN_TYPES:
        return "Type is invalid.", {}
    try:
        magnitude = float(amount) if amount not in (None, "") else None
    except (TypeError, ValueError):
        return "Amount must be a number.", {}
    if magnitude is None or magnitude <= 0:
        return "Amount must be greater than zero.", {}

    signed = magnitude if txn_type == "Deposit" else -magnitude
    return None, {"txn_date": parsed, "txn_type": txn_type, "amount": signed}
