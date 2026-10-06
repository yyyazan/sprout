"""What a ticker is: a company's stock, an index fund, or some other fund.

yfinance's `quoteType` alone can't answer it — MUU is an "ETF" that is really a
2x single-stock bet, IBIT holds bitcoin, ARKK is actively managed. So a fund counts
as an index fund only when its category is a broad one (a market-cap/style box, a
region, a core bond, an allocation fund) and its summary doesn't say it's actively
managed. Everything else that isn't a plain stock is just a "fund".
"""
from __future__ import annotations

import re

STOCK, INDEX, FUND = "stock", "index", "fund"

_FUND_TYPES = {"ETF", "MUTUALFUND"}

# Morningstar categories that read as "the market": the 9-box, regions, core bonds,
# and the allocation / target-date funds. Leveraged ("Trading--"), crypto ("Digital
# Assets"), commodities and single-sector categories are deliberately not here.
_BROAD = re.compile(
    r"^(Large|Mid-Cap|Small|Foreign|Diversified|World|Global Large|Europe|Pacific|Japan|China|India|"
    r"Latin|Intermediate|Short-Term|Long-Term|Ultrashort|Target-Date|Allocation|Moderate|Conservative|"
    r"Aggressive)",
    re.I,
)
_ACTIVE = re.compile(r"actively[\s-]*managed", re.I)


def kind_of(info: dict) -> str:
    """'stock' | 'index' | 'fund' from a yfinance `.info` dict."""
    if str(info.get("quoteType") or "").upper() not in _FUND_TYPES:
        return STOCK
    category = str(info.get("category") or "")
    if _BROAD.match(category) and not _ACTIVE.search(str(info.get("longBusinessSummary") or "")):
        return INDEX
    return FUND
