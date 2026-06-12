"""One-off: fill trades.price for rows logged before the column existed.

Each NULL-price trade gets the split-adjusted close on its trade date (nearest
trading day on or before — same `price_on_date` convention the API uses when a
trade is saved without a price). Idempotent: re-running only touches rows that
are still NULL, so it's safe to run again if a ticker's history was unavailable.

Usage:  .venv/bin/python scripts/backfill_trade_prices.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from portfolio.data import db, prices


def main() -> None:
    conn = db.connect()
    db.init_schema(conn)  # ensures the price column exists

    rows = conn.execute(
        "SELECT id, ticker, trade_date FROM trades WHERE price IS NULL ORDER BY ticker"
    ).fetchall()
    if not rows:
        print("Nothing to backfill — every trade already has a price.")
        return

    filled, missing = 0, []
    for r in rows:
        px = prices.price_on_date(r["ticker"], pd.Timestamp(r["trade_date"]))
        if px is None:
            missing.append((r["id"], r["ticker"], r["trade_date"]))
            continue
        conn.execute("UPDATE trades SET price = ? WHERE id = ?", (px, r["id"]))
        filled += 1
    conn.commit()

    print(f"Backfilled {filled}/{len(rows)} trades with closing prices.")
    for trade_id, ticker, trade_date in missing:
        print(f"  no price history: id={trade_id} {ticker} {trade_date} (left NULL)")


if __name__ == "__main__":
    main()
