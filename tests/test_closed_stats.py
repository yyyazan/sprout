"""closed_stats: the sold-side totals behind a ticker's lifetime P&L and return.
Hand-built FIFO rows, so no network."""
from __future__ import annotations

import pandas as pd
import pytest

from portfolio.analytics.realized import closed_stats

COLS = ["ticker", "shares", "buy_date", "sell_date", "buy_price", "sell_price", "realized_pnl"]


def _rows(*rows):
    return pd.DataFrame(rows, columns=COLS)


def test_totals_and_share_weighted_prices():
    r = _rows(
        ("AAA", 2.0, "2026-01-02", "2026-02-02", 10.0, 15.0, 10.0),
        ("AAA", 6.0, "2026-01-05", "2026-02-02", 20.0, 18.0, -12.0),
        ("BBB", 1.0, "2026-01-02", "2026-02-02", 5.0, 9.0, 4.0),
    )
    s = closed_stats(r, "AAA")
    assert s == {
        "realized": -2.0,
        "cost": 140.0,       # 2*10 + 6*20
        "shares": 8.0,
        "avgBuy": 17.5,      # 140 / 8
        "avgSell": 17.25,    # (2*15 + 6*18) / 8
    }


def test_lifetime_return_adds_the_open_lot():
    # sold half at a gain, still holding the rest at a loss: return is total P&L
    # over everything bought, not either half on its own
    s = closed_stats(_rows(("AAA", 5.0, "2026-01-02", "2026-02-02", 10.0, 20.0, 50.0)), "AAA")
    open_cost, open_pnl = 5 * 10.0, -15.0
    pct = (s["realized"] + open_pnl) / (s["cost"] + open_cost) * 100
    assert pct == pytest.approx(35.0)


def test_never_sold_is_none():
    assert closed_stats(_rows(("BBB", 1.0, "2026-01-02", "2026-02-02", 5.0, 9.0, 4.0)), "AAA") is None
    assert closed_stats(pd.DataFrame(), "AAA") is None  # no sells at all → fifo_realized returns no columns


def test_flat_exit_still_counts_as_sold():
    # sold at exactly the buy price: $0 realized, but it was held, so not None
    s = closed_stats(_rows(("AAA", 3.0, "2026-01-02", "2026-02-02", 10.0, 10.0, 0.0)), "AAA")
    assert s["realized"] == 0.0 and s["shares"] == 3.0


def test_unpriced_rows_are_skipped():
    r = _rows(
        ("AAA", 1.0, "2026-01-02", "2026-02-02", None, 15.0, 0.0),
        ("AAA", 2.0, "2026-01-05", "2026-02-02", 10.0, 12.0, 4.0),
    )
    s = closed_stats(r, "AAA")
    assert s["shares"] == 2.0 and s["cost"] == 20.0
