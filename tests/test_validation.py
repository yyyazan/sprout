"""Unit tests for api/validation.py — pure functions, no DB/HTTP involved."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from api.validation import parse_date, validate_trade, validate_txn


def _snapshot(held: dict[str, float] | None = None):
    from types import SimpleNamespace

    return SimpleNamespace(open_positions=pd.Series(held or {}, dtype=float))


TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()


# ── parse_date ──────────────────────────────────────────────────────────────

def test_parse_date_accepts_iso_string():
    assert parse_date("2024-08-20") == date(2024, 8, 20)


def test_parse_date_truncates_timestamp_suffix():
    assert parse_date("2024-08-20T00:00:00") == date(2024, 8, 20)


def test_parse_date_rejects_garbage():
    assert parse_date("not-a-date") is None


def test_parse_date_rejects_empty():
    assert parse_date("") is None
    assert parse_date(None) is None


# ── validate_trade: ticker ──────────────────────────────────────────────────

def test_trade_requires_ticker():
    errors, _ = validate_trade("", "buy", 1, TODAY, 10, snapshot=_snapshot())
    assert "ticker" in errors


def test_trade_rejects_lowercase_leading_char():
    # TICKER_RE requires an uppercase first letter — lowercase input should
    # still pass since the value is upper-cased before the regex check.
    errors, clean = validate_trade("aapl", "buy", 1, TODAY, 10, snapshot=_snapshot())
    assert not errors
    assert clean["ticker"] == "AAPL"


def test_trade_rejects_invalid_ticker_chars():
    errors, _ = validate_trade("$$$", "buy", 1, TODAY, 10, snapshot=_snapshot())
    assert "ticker" in errors


# ── validate_trade: action / shares / price ─────────────────────────────────

def test_trade_rejects_bad_action():
    errors, _ = validate_trade("AAPL", "hold", 1, TODAY, 10, snapshot=_snapshot())
    assert "action" in errors


def test_trade_requires_shares():
    errors, _ = validate_trade("AAPL", "buy", None, TODAY, 10, snapshot=_snapshot())
    assert "shares" in errors


def test_trade_rejects_zero_or_negative_shares():
    errors, _ = validate_trade("AAPL", "buy", 0, TODAY, 10, snapshot=_snapshot())
    assert "shares" in errors
    errors, _ = validate_trade("AAPL", "buy", -5, TODAY, 10, snapshot=_snapshot())
    assert "shares" in errors


def test_trade_price_is_optional():
    errors, clean = validate_trade("AAPL", "buy", 1, TODAY, None, snapshot=_snapshot())
    assert not errors
    assert clean["price"] is None


def test_trade_rejects_negative_price():
    errors, _ = validate_trade("AAPL", "buy", 1, TODAY, -1, snapshot=_snapshot())
    assert "price" in errors


# ── validate_trade: date ────────────────────────────────────────────────────

def test_trade_rejects_invalid_date():
    errors, _ = validate_trade("AAPL", "buy", 1, "not-a-date", 10, snapshot=_snapshot())
    assert "date" in errors


def test_trade_rejects_future_date():
    errors, _ = validate_trade("AAPL", "buy", 1, TOMORROW, 10, snapshot=_snapshot())
    assert "date" in errors


def test_trade_accepts_today():
    errors, _ = validate_trade("AAPL", "buy", 1, TODAY, 10, snapshot=_snapshot())
    assert not errors


# ── validate_trade: sell-side held-shares check ─────────────────────────────

def test_sell_rejected_with_no_position():
    errors, _ = validate_trade("AAPL", "sell", 1, TODAY, 10, snapshot=_snapshot())
    assert "ticker" in errors
    assert "No open position" in errors["ticker"]


def test_sell_rejected_when_exceeding_held():
    errors, _ = validate_trade("AAPL", "sell", 5, TODAY, 10, snapshot=_snapshot({"AAPL": 2}))
    assert "shares" in errors
    assert "Exceeds" in errors["shares"]


def test_sell_allowed_up_to_held_amount():
    errors, clean = validate_trade("AAPL", "sell", 2, TODAY, 10, snapshot=_snapshot({"AAPL": 2}))
    assert not errors
    assert clean["shares"] == 2


def test_sell_allowed_within_float_epsilon_of_held():
    # 0.1 + 0.2 style float drift shouldn't false-positive an "exceeds held" error.
    errors, _ = validate_trade("AAPL", "sell", 2.0000001, TODAY, 10, snapshot=_snapshot({"AAPL": 2}))
    assert not errors


def test_buy_does_not_consult_snapshot_at_all():
    # A buy for a ticker with zero holdings should never trip the sell-only check.
    errors, clean = validate_trade("TSLA", "buy", 3, TODAY, 200, snapshot=_snapshot())
    assert not errors
    assert clean["action"] == "buy"


# ── validate_txn ─────────────────────────────────────────────────────────────

def test_txn_valid_deposit():
    error, clean = validate_txn(TODAY, "Deposit", 100)
    assert error is None
    assert clean["amount"] == 100


def test_txn_valid_withdrawal_is_signed_negative():
    error, clean = validate_txn(TODAY, "Withdrawal", 50)
    assert error is None
    assert clean["amount"] == -50


def test_txn_rejects_invalid_date():
    error, _ = validate_txn("nope", "Deposit", 10)
    assert error is not None


def test_txn_rejects_future_date():
    error, _ = validate_txn(TOMORROW, "Deposit", 10)
    assert error is not None


def test_txn_rejects_bad_type():
    error, _ = validate_txn(TODAY, "Transfer", 10)
    assert error is not None


def test_txn_rejects_nonpositive_amount():
    error, _ = validate_txn(TODAY, "Deposit", 0)
    assert error is not None
    error, _ = validate_txn(TODAY, "Deposit", -5)
    assert error is not None


def test_txn_rejects_non_numeric_amount():
    error, _ = validate_txn(TODAY, "Deposit", "lots")
    assert error is not None


@pytest.mark.parametrize("amount", [0.01, 1_000_000])
def test_txn_accepts_wide_amount_range(amount):
    error, clean = validate_txn(TODAY, "Deposit", amount)
    assert error is None
    assert clean["amount"] == amount
