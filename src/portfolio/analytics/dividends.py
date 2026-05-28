"""monthly dividends

in: current positions
out: monthly dividends
"""
from __future__ import annotations

import pandas as pd

from portfolio.data import loader, prices as prices_mod
from portfolio.analytics import positions as pos_mod
from pathlib import Path
DATA_DIR = Path(__file__).parents[3] / "data"


trades = loader.load_trades(DATA_DIR / "trades.csv")

print(trades.head())