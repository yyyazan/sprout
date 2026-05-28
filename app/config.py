"""Runtime config from environment.

Defaults are tuned for local dev. Railway sets DATA_DIR=/data, supplies the
auth pair, and overrides BENCHMARK_TICKERS only if you want something other
than SPY+QQQ.
"""
from __future__ import annotations

import os
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
BENCHMARK_TICKERS = tuple(
    t.strip().upper() for t in os.environ.get("BENCHMARK_TICKERS", "SPY,QQQ").split(",") if t.strip()
)
SAR_USD_PEG = float(os.environ.get("SAR_USD_PEG", "3.75"))
MONTHLY_SAVINGS_TARGET = float(os.environ.get("MONTHLY_SAVINGS_TARGET", "1000"))

DASH_AUTH_USER = os.environ.get("DASH_AUTH_USER", "")
DASH_AUTH_PASS_BCRYPT = os.environ.get("DASH_AUTH_PASS_BCRYPT", "")

# When unset (e.g. local first-run), allow the app to boot without auth.
# Railway deploys MUST set both env vars.
AUTH_ENABLED = bool(DASH_AUTH_USER and DASH_AUTH_PASS_BCRYPT)
