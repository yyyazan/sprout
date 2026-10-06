"""Fund support: the /api/kinds map, the stock view's fund block, and kind on the
dividend items. yfinance is stubbed throughout — no network."""
from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from tests.test_entries_trades import add_trade


def test_kinds_covers_traded_and_listed_tickers(client, monkeypatch):
    from portfolio.data import prices

    add_trade(client, ticker="VOO")
    add_trade(client, ticker="AAPL")
    client.post("/api/lists", json={"name": "Funds", "tickers": ["MUU"]})
    profiles = {"VOO": {"kind": "index"}, "AAPL": {"kind": "stock"}, "MUU": {"kind": "fund"}}
    monkeypatch.setattr(prices, "profile", lambda t: profiles.get(t, {}))

    assert client.get("/api/kinds").json() == {"AAPL": "stock", "MUU": "fund", "VOO": "index"}


def test_kinds_defaults_to_stock_when_a_profile_fails(client, monkeypatch):
    from portfolio.data import prices

    add_trade(client, ticker="XYZ")

    def boom(t):
        raise RuntimeError("yahoo down")

    monkeypatch.setattr(prices, "profile", boom)
    assert client.get("/api/kinds").json() == {"XYZ": "stock"}


def _fake_ticker(ops, top, sectors):
    return lambda sym: SimpleNamespace(
        funds_data=SimpleNamespace(fund_operations=ops, top_holdings=top, sector_weightings=sectors)
    )


def test_fund_block_reads_cost_holdings_and_sectors(monkeypatch):
    from api.routers import stock

    ops = pd.DataFrame(
        {"VOO": {"Annual Report Expense Ratio": 0.0003}, "Category Average": {"Annual Report Expense Ratio": 0.0072}}
    )
    top = pd.DataFrame(
        {"Name": ["NVIDIA Corp", "Apple Inc"], "Holding Percent": [0.08, 0.07]}, index=pd.Index(["NVDA", "AAPL"], name="Symbol")
    )
    monkeypatch.setattr(stock.yf, "Ticker", _fake_ticker(ops, top, {"technology": 0.39, "energy": 0.0, "financial_services": 0.12}))
    stock._fund_cache.clear()

    f = stock._fund("VOOX", {"category": "Large Blend", "fundFamily": "Vanguard", "netExpenseRatio": 0.03, "totalAssets": 1e12, "yield": 0.0106})

    assert f["expense"] == pytest.approx(0.0003)            # netExpenseRatio is percent
    assert f["categoryExpense"] == pytest.approx(0.0072)
    assert f["holdings"] == [
        {"symbol": "NVDA", "name": "NVIDIA Corp", "weight": 0.08},
        {"symbol": "AAPL", "name": "Apple Inc", "weight": 0.07},
    ]
    assert [s["name"] for s in f["sectors"]] == ["Technology", "Financials"]   # biggest first, zero dropped
    assert f["category"] == "Large Blend" and f["yield"] == 0.0106


def test_fund_block_survives_missing_pieces(monkeypatch):
    # leveraged / crypto funds: Yahoo has no holdings and a 0 category average
    from api.routers import stock

    ops = pd.DataFrame({"MUUX": {"Annual Report Expense Ratio": 0.0101}, "Category Average": {"Annual Report Expense Ratio": 0.0}})
    monkeypatch.setattr(stock.yf, "Ticker", _fake_ticker(ops, pd.DataFrame(columns=["Name", "Holding Percent"]), {}))
    stock._fund_cache.clear()

    f = stock._fund("MUUX", {"category": "Trading--Leveraged Equity"})

    assert f["expense"] == pytest.approx(0.0101)            # falls back to the ops table
    assert f["categoryExpense"] is None                     # a 0 average isn't a comparison
    assert f["holdings"] == [] and f["sectors"] == []


def test_fund_block_with_no_funds_data(monkeypatch):
    from api.routers import stock

    def boom(sym):
        raise RuntimeError("no funds data")

    monkeypatch.setattr(stock.yf, "Ticker", boom)
    stock._fund_cache.clear()
    f = stock._fund("NOPE", {"category": "Large Blend", "netExpenseRatio": 0.1})
    assert f["expense"] == pytest.approx(0.001) and f["holdings"] == []


def test_dividend_items_carry_kind():
    from portfolio.analytics import dividends

    pnl = pd.DataFrame({"shares": [10.0, 5.0], "market_value": [1000.0, 500.0]}, index=["VOO", "AAPL"])
    cards = [{"ticker": "VOO", "company_name": "Vanguard S&P 500", "kind": "index"}, {"ticker": "AAPL", "company_name": "Apple"}]
    orig = dividends._annual_per_share
    dividends._annual_per_share = lambda t, now: 4.0
    try:
        out = dividends.monthly_dividends(pnl, cards)
    finally:
        dividends._annual_per_share = orig
    assert {i["t"]: i["kind"] for i in out["items"]} == {"VOO": "index", "AAPL": "stock"}
