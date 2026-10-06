"""kind_of: stock vs index fund vs other fund, on the shapes yfinance actually returns
for tickers this portfolio has held. No network."""
from __future__ import annotations

import pytest

from portfolio.analytics.kinds import kind_of


def _etf(category, summary=""):
    return {"quoteType": "ETF", "category": category, "longBusinessSummary": summary}


@pytest.mark.parametrize("category", [
    "Large Blend", "Large Growth", "Small Blend", "Mid-Cap Growth", "Foreign Large Blend",
    "Diversified Emerging Mkts", "World Large-Stock Blend", "Intermediate Core Bond",
])
def test_broad_categories_are_index_funds(category):
    assert kind_of(_etf(category, "indexing approach designed to track the performance of the index")) == "index"


@pytest.mark.parametrize("category", [
    "Trading--Leveraged Equity", "Trading--Inverse Equity", "Digital Assets",
    "Technology", "Commodities Focused", "Equity Energy", "",
])
def test_leveraged_crypto_sector_are_other_funds(category):
    assert kind_of(_etf(category)) == "fund"


def test_actively_managed_is_not_an_index_fund_even_in_a_broad_category():
    # ARKK reports "Mid-Cap Growth"
    assert kind_of(_etf("Mid-Cap Growth", 'The fund is an actively-managed exchange-traded fund ("ETF")')) == "fund"
    assert kind_of(_etf("Large Blend", "an Actively Managed fund")) == "fund"


def test_mutual_funds_count():
    assert kind_of({"quoteType": "MUTUALFUND", "category": "Large Blend"}) == "index"


@pytest.mark.parametrize("info", [{}, {"quoteType": "EQUITY"}, {"quoteType": "EQUITY", "category": "Large Blend"}, {"quoteType": None}])
def test_everything_else_is_a_stock(info):
    assert kind_of(info) == "stock"
