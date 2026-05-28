"""Module-level portfolio snapshot.

Pipeline runs once at app boot. Pages import `get_snapshot()` to read; the
result is cached for the process lifetime. Restart the gunicorn worker to
pick up new prices or new CSV rows. (DuckDB cache + scheduled refresh
land in M2.5+.)
"""
from __future__ import annotations

from portfolio.pipeline import PortfolioSnapshot, run

from app.config import BENCHMARK_TICKERS, DATA_DIR

_SNAPSHOT: PortfolioSnapshot | None = None


def get_snapshot() -> PortfolioSnapshot:
    global _SNAPSHOT
    if _SNAPSHOT is None:
        _SNAPSHOT = run(data_dir=DATA_DIR, benchmarks=BENCHMARK_TICKERS)
    return _SNAPSHOT


def refresh() -> PortfolioSnapshot:
    global _SNAPSHOT
    _SNAPSHOT = None
    return get_snapshot()
