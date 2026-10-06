"""One-off: fill trades.price from real fill prices exported from a spreadsheet.

Old trades were imported without a price, so every calculation fell back to that
day's close (`prices.price_on_date`) and the Log showed a dash. This writes the
actual fills in instead.

Sprout's shares and dates are the source of truth; ONLY the price comes from the
sheet. The sheet's own dates/units are just evidence for pairing a fill with a
Sprout trade. Rules:

  * pair within (ticker, action), sheet date within --max-days (35) of the trade date —
    wide on purpose: the range check below is what validates a pairing, and every
    shifted pairing is listed so it can be eyeballed
  * a pairing is valid only if the fill falls inside that ticker's real day range
    on the SPROUT trade date, in AS-TRADED terms (the DB stores pre-split prices;
    `adjusted_trade_price` divides by the split factor at runtime). A fill that
    only fits in today's split-adjusted terms is rejected, never converted
  * best overall assignment (scipy), preferring same date, then same units
  * a trade with no valid fill stays NULL — blank always means "estimated"

Dry-run by default: applies the update in a transaction, recomputes free cash /
open cost / realized P&L, prints what moved (plus a comparison with the sheet's
own realized totals), and rolls back. `--write` backs up the DB first.

Inputs (CSV, no spreadsheet dependency):
  --fills    sheet_row,date,action,ticker,units,price      (default data/sheet_fills.csv)
  --compare  ticker,realized                               (optional, the sheet's totals)

Usage:  .venv/bin/python scripts/import_sheet_fills.py --compare data/sheet_realized.csv
        .venv/bin/python scripts/import_sheet_fills.py --write
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import linear_sum_assignment

from portfolio.analytics import cash as cash_mod
from portfolio.analytics import cost_basis as cb_mod
from portfolio.analytics import positions as pos_mod
from portfolio.analytics import realized as real_mod
from portfolio.data import db, loader, prices

RANGE_TOL = 0.012   # fills a hair outside the day's print (extended hours, rounding)
BIG = 1e6


def raw_ohlc(ticker: str) -> pd.DataFrame:
    """Daily Low/High, split-adjusted but NOT dividend-adjusted. Empty if unavailable."""
    try:
        h = yf.Ticker(prices.yf_symbol(ticker).replace(".", "-")).history(period="max", auto_adjust=False)
        h.index = h.index.tz_localize(None)
        return h[["Low", "High"]].dropna()
    except Exception:
        return pd.DataFrame(columns=["Low", "High"])


def day_range(ohlc: pd.DataFrame, date: pd.Timestamp) -> tuple[float, float] | None:
    """(low, high) for the day; a non-trading date spans the sessions around it."""
    if ohlc.empty:
        return None
    if date in ohlc.index:
        r = ohlc.loc[date]
        return float(r["Low"]), float(r["High"])
    prev, nxt = ohlc[ohlc.index < date].tail(1), ohlc[ohlc.index > date].head(1)
    both = pd.concat([prev, nxt])
    return (float(both["Low"].min()), float(both["High"].max())) if not both.empty else None


def fits(rng: tuple[float, float] | None, px: float, factor: float, adjusted: bool = False) -> bool | None:
    """Is `px` inside the day's range? As-traded terms scale the (split-adjusted) range by
    the cumulative later-split factor; None when there is no history to test against."""
    if rng is None:
        return None
    f = 1.0 if adjusted else factor
    return rng[0] * f * (1 - RANGE_TOL) <= px <= rng[1] * f * (1 + RANGE_TOL)


def fingerprint(conn, user_id: int, splits: dict) -> dict:
    trades = loader.load_trades_db(user_id, conn)
    txn = loader.load_transactions_db(user_id, conn)
    ta = pos_mod.split_adjust(trades, splits)
    open_pos = pos_mod.open_positions(ta)
    cost = cb_mod.weighted_avg_cost(ta, open_pos.index.tolist()) * open_pos
    realized = real_mod.fifo_realized(ta)
    return {
        "cash": cash_mod.free_cash(ta, txn, db.reconciliation_offset(conn, user_id)),
        "cost": cost,
        "rows": realized,
    }


def realized_by(rows: pd.DataFrame, upto: pd.Timestamp | None = None) -> pd.Series:
    if rows.empty:
        return pd.Series(dtype=float)
    if upto is not None:
        rows = rows[pd.to_datetime(rows["sell_date"]) <= upto]
    return rows.groupby("ticker")["realized_pnl"].sum()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fills", default="data/sheet_fills.csv")
    ap.add_argument("--compare", default=None, help="CSV of ticker,realized from the sheet")
    ap.add_argument("--user", type=int, default=db.DEFAULT_USER_ID)
    ap.add_argument("--max-days", type=int, default=35, help="how far a sheet date may sit from the Sprout date")
    ap.add_argument("--keep-cash", action="store_true",
                    help="re-base the cash reconciliation offset so free cash stays where it is")
    ap.add_argument("--show", nargs="*", default=[], metavar="TICKER", help="print every pairing for these tickers")
    ap.add_argument("--write", action="store_true", help="commit (after a backup); default is a dry run")
    args = ap.parse_args()

    F = pd.read_csv(args.fills, parse_dates=["date"])
    F["units"] = F["units"].astype(float)

    conn = db.connect()
    db.init_schema(conn)
    D = pd.read_sql_query(
        "SELECT id, ticker, action, shares, trade_date FROM trades "
        "WHERE user_id = ? AND price IS NULL ORDER BY id",
        conn, params=(args.user,), parse_dates=["trade_date"],
    )
    if D.empty:
        print("Nothing to import — every trade already has a price.")
        return 0

    tickers = sorted(set(D["ticker"]) | set(F["ticker"]))
    all_tickers = [r["ticker"] for r in conn.execute("SELECT DISTINCT ticker FROM trades WHERE user_id = ?", (args.user,))]
    splits = prices.splits_map(all_tickers)
    with ThreadPoolExecutor(max_workers=8) as pool:
        ohlc = dict(zip(tickers, pool.map(raw_ohlc, tickers)))

    def factor_on(t: str, date: pd.Timestamp) -> float:
        return pos_mod.cumulative_split_factor(splits.get(t, pd.Series(dtype=float)), date)

    matches, unmatched_fills = [], []
    for (tk, act), fg in F.groupby(["ticker", "action"]):
        dg = D[(D.ticker == tk) & (D.action == act)]
        if dg.empty:
            for _, f in fg.iterrows():
                unmatched_fills.append((f, "no blank-price Sprout trade of this ticker/side"))
            continue
        fg, dg = fg.sort_values(["date", "sheet_row"]).reset_index(drop=True), dg.sort_values(["trade_date", "id"]).reset_index(drop=True)
        cost = np.full((len(fg), len(dg)), BIG)
        why = {}
        for i, f in fg.iterrows():
            for j, d in dg.iterrows():
                days = abs((f.date - d.trade_date).days)
                if days > args.max_days:
                    why.setdefault(i, "no Sprout trade within the date window")
                    continue
                rng = day_range(ohlc[tk], d.trade_date)
                fac = factor_on(tk, d.trade_date)
                ok = fits(rng, f.price, fac)
                if ok is False:
                    adj = fits(rng, f.price, fac, adjusted=True)
                    lo, hi = rng[0] * fac, rng[1] * fac
                    miss = (lo - f.price) / lo if f.price < lo else (f.price - hi) / hi
                    why[i] = (f"fill ${f.price:g} is {miss:.1%} outside {tk}'s range on {d.trade_date.date()} "
                              f"(${lo:g}–${hi:g})" + ("; only fits split-ADJUSTED terms" if adj else ""))
                    continue
                du = abs(f.units - d.shares) / max(f.units, d.shares, 1e-9)
                cost[i, j] = days + 8 * du + 1e-4 * abs(i - j) + (0.5 if ok is None else 0)
        rows, cols = linear_sum_assignment(cost)
        taken = set()
        for i, j in zip(rows, cols):
            if cost[i, j] >= BIG:
                continue
            f, d = fg.loc[i], dg.loc[j]
            taken.add(i)
            matches.append(dict(
                id=int(d.id), ticker=tk, action=act, db_date=d.trade_date, db_shares=d.shares,
                sheet_row=int(f.sheet_row), sheet_date=f.date, sheet_units=f.units, price=float(f.price),
                days=(d.trade_date - f.date).days, validated=fits(day_range(ohlc[tk], d.trade_date), f.price, factor_on(tk, d.trade_date)) is not None,
                factor=factor_on(tk, d.trade_date),
            ))
        for i, f in fg.iterrows():
            if i not in taken:
                unmatched_fills.append((f, why.get(i, "every candidate Sprout trade was taken by a better pairing")))

    M = pd.DataFrame(matches)
    matched_ids = set(M["id"]) if len(M) else set()
    left = D[~D.id.isin(matched_ids)]
    exact = int(((M.days == 0) & (abs(M.db_shares - M.sheet_units) < 1e-6)).sum())
    print(f"blank-price Sprout trades: {len(D)}   sheet fills: {len(F)}")
    print(f"paired: {len(M)}  (exact date+units {exact}, date shifted {int((M.days != 0).sum())}, "
          f"units differ {int((abs(M.db_shares - M.sheet_units) > 1e-6).sum())}, "
          f"no price history to validate against {int((~M.validated).sum())})")
    print(f"split-affected pairs (stored as-traded, no conversion): {int((M.factor != 1).sum())}")

    shifted = M[(M.days != 0) | (abs(M.db_shares - M.sheet_units) > 1e-6)].sort_values(["ticker", "db_date"])
    if len(shifted):
        print("\npaired despite a different date or units on the sheet (Sprout's values kept):")
        for _, m in shifted.iterrows():
            print(f"  {m.ticker:5s} {m.action:4s} db {m.db_date.date()} x{m.db_shares:g}   sheet {m.sheet_date.date()} x{m.sheet_units:g}  "
                  f"({m.days:+d}d)  ${m.price:g}")
    for tk in args.show:
        print(f"\nall pairings for {tk}:")
        for _, m in M[M.ticker == tk].sort_values("db_date").iterrows():
            print(f"  id{m.id:>3} {m.action:4s} {m.db_date.date()} x{m.db_shares:<7g} ← sheet row {m.sheet_row:>3} {m.sheet_date.date()} x{m.sheet_units:<7g} ${m.price:g}")
        blank = D[(D.ticker == tk) & ~D.id.isin(matched_ids)]
        for _, r in blank.iterrows():
            print(f"  id{r.id:>3} {r.action:4s} {r.trade_date.date()} x{r.shares:<7g} ← (no fill)")
    if unmatched_fills:
        print(f"\nsheet fills NOT used ({len(unmatched_fills)}):")
        for f, reason in sorted(unmatched_fills, key=lambda x: (x[0].ticker, x[0].date)):
            print(f"  row {int(f.sheet_row):>3} {f.ticker:5s} {f.action:4s} {f.date.date()} x{f.units:g} ${f.price:g}  — {reason}")
    print(f"\nSprout trades left blank ({len(left)}):")
    for tk, g in left.groupby("ticker"):
        print(f"  {tk:5s} " + ", ".join(f"id{int(r.id)} {r.action} {r.shares:g} {r.trade_date.date()}" for _, r in g.iterrows()))

    before = fingerprint(conn, args.user, splits)
    if args.write:
        backup = Path(db.DEFAULT_DB_PATH).parent / "backups" / f"portfolio-pre-fill-import-{datetime.now():%Y-%m-%dT%H%M%S}.db"
        backup.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(backup)) as dest:
            conn.backup(dest)
        print(f"\nBacked up to {backup}")
    conn.executemany("UPDATE trades SET price = ? WHERE id = ? AND price IS NULL",
                     [(round(p, 4), i) for p, i in zip(M["price"], M["id"])])
    after = fingerprint(conn, args.user, splits)

    # The cash offset is a plug calibrated against the old close-based trade prices, so
    # real fills move free cash by exactly the price differences. --keep-cash re-bases
    # the plug by that amount (same transaction) so displayed cash doesn't jump.
    rebase = None
    if args.keep_cash:
        old_off = db.reconciliation_offset(conn, args.user)
        new_off = old_off - (after["cash"] - before["cash"])
        row = db.reconciliation_row(conn, args.user)
        note = f"{(row['note'] if row and row['note'] else '').strip()} | offset re-based {old_off:+.2f} → {new_off:+.2f} for imported fills".strip(" |")
        conn.execute("UPDATE cash_reconciliation SET offset_usd = ?, reconciled_at = ?, note = ? WHERE user_id = ?",
                     (new_off, datetime.now().astimezone().isoformat(), note, args.user))
        rebase = (old_off, new_off)
        after["cash"] = before["cash"]

    print("\n── effect on Sprout's numbers ──")
    print(f"  free cash     {before['cash']:>12,.2f} → {after['cash']:>12,.2f}   ({after['cash'] - before['cash']:+,.2f})")
    if rebase:
        print(f"  cash offset   {rebase[0]:>12,.2f} → {rebase[1]:>12,.2f}   (re-based so cash is unchanged)")
    print(f"  open cost     {before['cost'].sum():>12,.2f} → {after['cost'].sum():>12,.2f}   ({after['cost'].sum() - before['cost'].sum():+,.2f})")
    rb, ra = realized_by(before["rows"]), realized_by(after["rows"])
    print(f"  realized P&L  {rb.sum():>12,.2f} → {ra.sum():>12,.2f}   ({ra.sum() - rb.sum():+,.2f})")
    d = ra.sub(rb, fill_value=0.0)
    d = d[d.abs() > 0.005].sort_values(key=lambda s: -s.abs())
    print("  biggest realized moves: " + ", ".join(f"{t} {v:+.2f}" for t, v in d.head(8).items()))
    for label, rows in (("before", before["rows"]), ("after ", after["rows"])):
        rk = rows[(rows.ticker == "RKLB") & (pd.to_datetime(rows.sell_date).dt.year == 2024)]
        print(f"  RKLB realized in 2024 {label}: {rk.realized_pnl.sum():,.2f}")

    if args.compare:
        S = pd.read_csv(args.compare).set_index("ticker")["realized"]
        upto = F["date"].max()
        mine = realized_by(after["rows"], upto)
        both = pd.concat([mine.rename("sprout"), S.rename("sheet")], axis=1).fillna(0.0)
        both["diff"] = both.sprout - both.sheet
        print(f"\n── Sprout realized (sells through {upto.date()}) vs the sheet's per-ticker realized ──")
        print(f"  total  sprout {both.sprout.sum():,.2f}   sheet {both.sheet.sum():,.2f}   diff {both['diff'].sum():+,.2f}")
        near = (both["diff"].abs() < 1.0).sum()
        print(f"  {near}/{len(both)} tickers agree within $1.00; largest gaps:")
        for t, r in both.reindex(both["diff"].abs().sort_values(ascending=False).index).head(12).iterrows():
            print(f"    {t:5s} sprout {r.sprout:>9,.2f}  sheet {r.sheet:>9,.2f}  diff {r['diff']:+9,.2f}")

    if not args.write:
        conn.rollback()
        print("\nDry run — rolled back, nothing written. Re-run with --write to commit.")
        return 0
    conn.commit()
    print(f"\nCommitted {len(M)} prices.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
