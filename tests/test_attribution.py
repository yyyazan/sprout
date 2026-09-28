"""Attribution must reconcile: the per-ticker contributions over any window add
up to the portfolio's $ change net of deposits/withdrawals (the chart measure).
Synthetic prices and a stubbed trade-price lookup, so no network."""
from __future__ import annotations

import pandas as pd
import pytest

from portfolio.analytics import attribution, cash, timeseries

DAYS = pd.bdate_range("2026-01-05", "2026-02-27")


def _prices():
    n = len(DAYS)
    return {
        "AAA": pd.Series([100 + i for i in range(n)], index=DAYS, dtype=float),        # steady climb
        "BBB": pd.Series([50 - 0.5 * i for i in range(n)], index=DAYS, dtype=float),   # steady bleed
        "CCC": pd.Series([20 + (i % 5) for i in range(n)], index=DAYS, dtype=float),   # chop, sold out
    }


def _trades():
    rows = [
        # ticker, action, shares, recorded price (None = that day's close), date
        ("AAA", "buy", 5, None, "2026-01-06"),
        ("BBB", "buy", 10, 49.0, "2026-01-07"),
        ("CCC", "buy", 20, None, "2026-01-08"),
        ("AAA", "buy", 2, None, "2026-01-20"),
        ("CCC", "sell", 20, 23.5, "2026-02-02"),   # fully closed: realized only
        ("BBB", "sell", 4, None, "2026-02-10"),    # partial
    ]
    df = pd.DataFrame(rows, columns=["ticker", "action", "shares", "price", "date"])
    df["date"] = pd.to_datetime(df["date"])
    df["signed_shares"] = df.apply(lambda r: r["shares"] if r["action"] == "buy" else -r["shares"], axis=1)
    df["split_factor"] = 1.0
    df["adj_shares"] = df["signed_shares"]
    return df


def _txn():
    df = pd.DataFrame(
        {"Date": pd.to_datetime(["2026-01-05", "2026-01-19", "2026-02-16"]), "Amount (USD)": [2000.0, 500.0, -300.0]}
    )
    return df


@pytest.fixture
def world(monkeypatch):
    prices = _prices()

    def trade_price(ticker, date, recorded=None, split_factor=1.0):
        if recorded is not None and not pd.isna(recorded):
            return float(recorded) / split_factor
        s = prices[ticker]
        return float(s[s.index <= date].iloc[-1])

    # cash.py prices trades through the prices module; point it at the same stub
    monkeypatch.setattr(cash.prices_mod, "adjusted_trade_price", trade_price)
    trades, txn = _trades(), _txn()
    daily = timeseries.daily_calendar(trades, txn, DAYS)
    equity = timeseries.portfolio_equity(trades, prices, daily, DAYS)
    cash_ts = cash.cash_timeseries(trades, txn, daily, 12.34).reindex(DAYS, method="ffill").fillna(0.0)
    _, _, net_inv = timeseries.capital_flows(txn, daily, DAYS)
    pnl = attribution.cumulative_pnl_by_ticker(trades, prices, daily, DAYS, trade_price=trade_price)
    return {"value": equity + cash_ts, "net": net_inv, "pnl": pnl}


@pytest.mark.parametrize("start,end", [
    ("2026-01-05", "2026-02-27"),   # everything
    ("2026-01-12", "2026-02-06"),   # spans a deposit and the CCC exit
    ("2026-02-09", "2026-02-20"),   # spans a partial sell and a withdrawal
    ("2026-01-07", "2026-01-08"),   # one session
])
def test_contributions_reconcile_to_net_change(world, start, end):
    v, net, pnl = world["value"], world["net"], world["pnl"]
    contrib = attribution.window_contributions(pnl, start, end)
    net_change = (v[end] - v[start]) - (net[end] - net[start])
    assert contrib.sum() == pytest.approx(net_change, abs=1e-6)


def test_signs_and_closed_positions(world):
    contrib = attribution.window_contributions(world["pnl"], "2026-01-05", "2026-02-27")
    assert contrib["AAA"] > 0            # rose while held
    assert contrib["BBB"] < 0            # bled while held
    # CCC: bought 20 @ close on Jan 8 (20 + 3 = 23), sold 20 @ 23.50 → +$10, then flat
    assert contrib["CCC"] == pytest.approx(20 * (23.5 - 23.0))
    after_exit = attribution.window_contributions(world["pnl"], "2026-02-03", "2026-02-27")
    assert after_exit["CCC"] == pytest.approx(0.0)
