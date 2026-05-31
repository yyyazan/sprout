"""FastAPI runtime config (ports the relevant bits of the old app/config.py).

Data paths (SQLite file, Parquet dir) are owned by portfolio.data.db /
portfolio.data.store and read from PORTFOLIO_DB / PORTFOLIO_PRICES there.
"""
from __future__ import annotations

import os

BENCHMARK_TICKERS = tuple(
    t.strip().upper()
    for t in os.environ.get("BENCHMARK_TICKERS", "SPY,QQQ").split(",")
    if t.strip()
)
MONTHLY_SAVINGS_TARGET = float(os.environ.get("MONTHLY_SAVINGS_TARGET", "1000"))

# Vite dev origins allowed during the parallel build.
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
