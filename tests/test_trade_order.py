"""Same-day trades run buys first, then in entry order. A date-only sort is
unstable, so a same-day sell could be processed before its own buy and FIFO
silently dropped it from realized P&L (TSLA / DJT were off by ~$15 each).
Recorded prices on every row, so no network."""
from __future__ import annotations

import pandas as pd

from portfolio.analytics import positions as pos
from portfolio.analytics import realized as real
from portfolio.data import loader


def _frame():
    rows, i = [], 0
    # enough unrelated, tied-date rows that pandas' global sort leaves the small-array path
    for d in pd.date_range("2025-01-02", periods=40, freq="B"):
        for tk in ("F1", "F2"):
            i += 1
            rows.append((i, tk, "buy", 1.0, 10.0, d))
    day = pd.Timestamp("2025-06-02")
    # a same-day round trip on a ticker with no inventory, logged SELL FIRST (lower id)
    rows.append((i + 1, "BBB", "sell", 3.0, 20.0, day))
    rows.append((i + 2, "BBB", "buy", 3.0, 15.0, day))
    return pd.DataFrame(rows, columns=["id", "ticker", "action", "shares", "price", "date"])


def test_same_day_buy_sorts_before_sell():
    t = loader._normalize_trades(_frame())
    bbb = t[t.ticker == "BBB"]
    assert bbb.action.tolist() == ["buy", "sell"]
    assert t.date.is_monotonic_increasing


def test_fifo_matches_a_same_day_round_trip_logged_sell_first():
    t = loader._normalize_trades(_frame())
    r = real.fifo_realized(pos.split_adjust(t, {}))
    bbb = r[r.ticker == "BBB"]
    assert bbb.shares.sum() == 3.0                      # the sell was matched, not dropped
    assert round(bbb.realized_pnl.sum(), 6) == 15.0     # 3 × (20 − 15)
