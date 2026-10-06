"""One-off: fill trades.price for rows logged before the column existed.

A NULL price is not "missing" to the app — every calculation falls back to
`prices.price_on_date` at compute time — it just never shows in the Log. This
writes a price into the row so it does.

Stored prices are AS TRADED: `adjusted_trade_price` divides a stored price by
the cumulative split factor, so the value saved here must be in the terms of
the day (pre-split), i.e. the split-adjusted close × that factor. Saving the
split-adjusted close directly would be divided a second time and misstate
every ticker that split after the trade.

--basis picks which close:
  adjusted  yfinance's history as the app already uses it (split- AND
            dividend-adjusted). Every number in the app stays the same, but the
            Log shows prices a broker never printed (VOO 2025-03-03: $525.84).
  close     the real closing price (split-adjusted only), what the broker
            showed. The Log matches reality; cost basis / cash move slightly
            because dividend adjustment drops out.

Dry-run by default: it applies the update inside a transaction, recomputes
free cash / open cost basis / realized P&L per user, prints what moved, and
rolls back. `--write` backs the DB up first, then commits. Idempotent: only
rows still NULL are touched, so re-running is safe.

Usage:  .venv/bin/python scripts/backfill_trade_prices.py --basis close
        .venv/bin/python scripts/backfill_trade_prices.py --basis close --write
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import yfinance as yf

from portfolio.analytics import cash as cash_mod
from portfolio.analytics import cost_basis as cb_mod
from portfolio.analytics import positions as pos_mod
from portfolio.analytics import realized as real_mod
from portfolio.data import db, loader, prices

TOLERANCE = 0.05  # $ — adjusted basis must leave every user's numbers within this


def _raw_close_series(ticker: str) -> pd.Series:
    """Split-adjusted, NOT dividend-adjusted closes (what the broker printed,
    up to later splits). Empty for delisted / unknown tickers."""
    try:
        h = yf.Ticker(prices.yf_symbol(ticker)).history(period="max", auto_adjust=False)
    except Exception:
        return pd.Series(dtype=float)
    if h is None or h.empty:
        return pd.Series(dtype=float)
    h.index = h.index.tz_localize(None) if h.index.tz is not None else h.index
    return h["Close"].dropna()


def _on_or_before(series: pd.Series, date: pd.Timestamp) -> float | None:
    if series.empty:  # delisted ticker: an empty Series has no date index to compare
        return None
    valid = series[series.index <= date]
    return float(valid.iloc[-1]) if not valid.empty else None


def fingerprint(conn, user_id: int, splits: dict) -> dict:
    """Everything that reads a trade price: free cash, open cost, realized P&L."""
    trades = loader.load_trades_db(user_id, conn)
    if trades.empty:
        return {"cash": 0.0, "cost": pd.Series(dtype=float), "realized": pd.Series(dtype=float)}
    txn = loader.load_transactions_db(user_id, conn)
    ta = pos_mod.split_adjust(trades, splits)
    open_pos = pos_mod.open_positions(ta)
    cost = cb_mod.weighted_avg_cost(ta, open_pos.index.tolist()) * open_pos
    realized = real_mod.fifo_realized(ta)
    return {
        "cash": cash_mod.free_cash(ta, txn, db.reconciliation_offset(conn, user_id)),
        "cost": cost,
        "realized": real_mod.realized_summary(realized) if not realized.empty else pd.Series(dtype=float),
    }


def _delta(before: pd.Series, after: pd.Series) -> pd.Series:
    d = after.sub(before, fill_value=0.0)
    return d[d.abs() > 0.005].sort_values(key=lambda s: -s.abs())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--basis", choices=["adjusted", "close"], required=True)
    ap.add_argument("--write", action="store_true", help="commit (after a backup); default is a dry run")
    args = ap.parse_args()

    conn = db.connect()
    db.init_schema(conn)  # ensures the price column exists

    rows = conn.execute(
        "SELECT id, user_id, ticker, action, shares, trade_date FROM trades "
        "WHERE price IS NULL ORDER BY user_id, ticker, trade_date"
    ).fetchall()
    if not rows:
        print("Nothing to backfill — every trade already has a price.")
        return 0

    tickers = sorted({r["ticker"] for r in rows})
    all_tickers = [r["ticker"] for r in conn.execute("SELECT DISTINCT ticker FROM trades")]
    splits = prices.splits_map(all_tickers)
    raw = {}
    if args.basis == "close":
        with ThreadPoolExecutor(max_workers=8) as pool:
            raw = dict(zip(tickers, pool.map(_raw_close_series, tickers)))

    users = sorted({r["user_id"] for r in rows})
    before = {u: fingerprint(conn, u, splits) for u in users}

    updates, missing, split_rows = [], [], []   # updates: (stored price, trade id)
    for r in rows:
        date = pd.Timestamp(r["trade_date"])
        if args.basis == "adjusted":
            px = prices.price_on_date(r["ticker"], date)
        else:
            px = _on_or_before(raw[r["ticker"]], date)
        if px is None:
            missing.append(r)
            continue
        factor = pos_mod.cumulative_split_factor(splits.get(r["ticker"], pd.Series(dtype=float)), date)
        stored = px * factor
        if args.basis == "close":
            # real closes are cents (or 4dp under $1); the × factor leaves float noise (1329.9001)
            stored = round(stored, 2 if stored >= 1 else 4)
        else:
            stored = round(stored, 4)
        updates.append((stored, r["id"]))
        if factor != 1:
            split_rows.append((r["ticker"], r["trade_date"], factor, px, stored))

    if args.write:  # snapshot the untouched file before the first UPDATE
        backup = Path(db.DEFAULT_DB_PATH).parent / "backups" / f"portfolio-pre-price-backfill-{datetime.now():%Y-%m-%dT%H%M%S}.db"
        backup.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(backup)) as dest:
            conn.backup(dest)
        print(f"Backed up to {backup}")

    # applied inside one transaction: the fingerprint below reads the pending
    # values, and nothing lands until the commit at the bottom
    conn.executemany("UPDATE trades SET price = ? WHERE id = ? AND price IS NULL", updates)
    after = {u: fingerprint(conn, u, splits) for u in users}

    print(f"basis={args.basis}  {'filling' if args.write else 'would fill'} {len(updates)}/{len(rows)} rows "
          f"({len(split_rows)} on tickers that split after the trade)")
    for t, d, f, px, stored in split_rows[:6]:
        print(f"  split  {t:5s} {d}  ×{f:g}  close {px:.4f} → stored {stored:.4f}")
    if len(split_rows) > 6:
        print(f"  … {len(split_rows) - 6} more split rows")
    for r in missing:
        print(f"  no price history: id={r['id']} {r['ticker']} {r['trade_date']} (left NULL)")

    worst = 0.0
    for u in users:
        b, a = before[u], after[u]
        dc = a["cash"] - b["cash"]
        dcost = _delta(b["cost"], a["cost"])
        dreal = _delta(b["realized"], a["realized"])
        worst = max(worst, abs(dc), *(dcost.abs().tolist() or [0]), *(dreal.abs().tolist() or [0]))
        print(f"\nuser {u}")
        print(f"  free cash      {b['cash']:>12,.2f} → {a['cash']:>12,.2f}   ({dc:+,.2f})")
        print(f"  open cost      {b['cost'].sum():>12,.2f} → {a['cost'].sum():>12,.2f}   ({a['cost'].sum() - b['cost'].sum():+,.2f})")
        print(f"  realized P&L   {b['realized'].sum():>12,.2f} → {a['realized'].sum():>12,.2f}   ({a['realized'].sum() - b['realized'].sum():+,.2f})")
        for label, d in (("open cost", dcost), ("realized", dreal)):
            if len(d):
                moved = ", ".join(f"{t} {v:+.2f}" for t, v in d.head(6).items())
                print(f"    {label} moved on {len(d)} tickers: {moved}")

    if args.basis == "adjusted" and worst > TOLERANCE:
        conn.rollback()
        print(f"\nABORT: adjusted basis should leave every number unchanged but moved by up to ${worst:,.2f}. Rolled back.")
        return 1

    if not args.write:
        conn.rollback()
        print("\nDry run — rolled back, nothing written. Re-run with --write to commit.")
        return 0

    conn.commit()
    print(f"\nCommitted {len(updates)} prices.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
