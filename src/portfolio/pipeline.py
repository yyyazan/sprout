"""Portfolio pipeline — runs the full notebook flow once and returns a snapshot.

This is the single entry point the Dash app calls at boot. It pulls everything
yfinance-related and performs every analytics computation, then returns a
typed snapshot the pages can read from. Re-running the pipeline picks up new
prices and new CSV rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from portfolio.analytics import (
    cash as cash_mod,
    cost_basis as cb_mod,
    positions as pos_mod,
    realized as real_mod,
    returns as ret_mod,
    risk as risk_mod,
    timeseries as ts_mod,
)
from portfolio.data import loader, prices as prices_mod


@dataclass(frozen=True)
class PortfolioSnapshot:
    # Holdings & P&L
    open_positions: pd.Series          # ticker -> adj shares
    pnl: pd.DataFrame                  # cols: shares, cost_basis, current_price, total_invested, market_value, unrealized_pnl, return_pct
    realized: pd.DataFrame             # FIFO match rows
    realized_summary: pd.Series        # ticker -> realized $

    # Cash
    free_cash: float                   # KPI value (includes reconciliation, matches broker)

    # Time series (indexed by trading days, trimmed to first meaningful day)
    portfolio_value_ts: pd.Series      # equity + cash daily
    portfolio_equity_ts: pd.Series     # equity-only
    cash_ts: pd.Series                 # daily cash balance (includes reconciliation)
    spy_ts: pd.Series                  # parallel SPY portfolio value
    qqq_ts: pd.Series                  # parallel QQQ portfolio value

    # Capital flows
    cumulative_deposits: pd.Series
    cumulative_withdrawals: pd.Series
    net_invested: pd.Series

    # TWR (cumulative decimal)
    twr_portfolio: pd.Series
    twr_spy: pd.Series
    twr_qqq: pd.Series

    # Risk (scalars over the trimmed window)
    max_drawdown_portfolio: float
    max_drawdown_spy: float
    max_drawdown_qqq: float
    sharpe_portfolio: float
    sharpe_spy: float
    sharpe_qqq: float

    # Savings / activity
    monthly_deposits: float
    last_txn_date: pd.Timestamp | None

    # Convenience
    last_updated: pd.Timestamp


def _current_month_deposits(txn: pd.DataFrame) -> float:
    today = pd.Timestamp.today()
    month = (txn["Date"].dt.year == today.year) & (txn["Date"].dt.month == today.month)
    deposits = txn["Amount (USD)"] > 0
    return float(txn.loc[month & deposits, "Amount (USD)"].sum())


def _last_txn_date(txn: pd.DataFrame) -> pd.Timestamp | None:
    return txn["Date"].max() if len(txn) else None


def run(data_dir: str | Path = "data", benchmarks: tuple[str, ...] = ("SPY", "QQQ")) -> PortfolioSnapshot:
    data_dir = Path(data_dir)

    # ── 1. Load CSVs ────────────────────────────────────────────────────────
    trades_raw = loader.load_trades(data_dir / "trades.csv")
    txn = loader.load_transactions(data_dir / "transactions.csv")

    # ── 2. Splits + adj_shares ──────────────────────────────────────────────
    tickers = trades_raw["ticker"].unique().tolist()
    splits_by_ticker = {t: prices_mod.splits(t) for t in tickers}
    trades_adj = pos_mod.split_adjust(trades_raw, splits_by_ticker)

    # ── 3. Open positions ───────────────────────────────────────────────────
    open_pos = pos_mod.open_positions(trades_adj)
    open_tickers = open_pos.index.tolist()

    # ── 4. Price history (open + closed tickers) ───────────────────────────
    all_history = prices_mod.histories(tickers)

    # ── 5. Spot prices for open tickers (drop tickers with no live price) ──
    spot_prices = {t: prices_mod.spot(t) for t in open_tickers}
    spot_prices = {t: p for t, p in spot_prices.items() if p is not None}

    # ── 6. Cost basis + unrealized P&L ──────────────────────────────────────
    cost_basis = cb_mod.weighted_avg_cost(trades_adj, open_tickers)
    pnl = cb_mod.unrealized_pnl(open_pos, cost_basis, spot_prices)

    # ── 7. Realized P&L (FIFO) ──────────────────────────────────────────────
    realized = real_mod.fifo_realized(trades_adj)
    realized_summary = real_mod.realized_summary(realized)

    # ── 8. Free cash ────────────────────────────────────────────────────────
    fc = cash_mod.free_cash(trades_adj, txn)

    # ── 9. Calendars + benchmark price series ──────────────────────────────
    bench_history = {b: prices_mod.history_from(b, trades_raw["date"].min()) for b in benchmarks}
    trading_days = bench_history[benchmarks[0]].index
    daily = ts_mod.daily_calendar(trades_raw, txn, trading_days)
    bench_prices = {b: bench_history[b].reindex(trading_days, method="ffill") for b in benchmarks}

    # ── 10. Portfolio equity, cash, total value series ─────────────────────
    equity_ts = ts_mod.portfolio_equity(trades_adj, all_history, daily, trading_days)
    cash_ts = cash_mod.cash_timeseries(trades_adj, txn, daily).reindex(trading_days, method="ffill").fillna(0.0)
    total_value_ts = equity_ts + cash_ts

    # ── 11. Parallel benchmark portfolios ──────────────────────────────────
    bench_value_ts = {
        b: ts_mod.benchmark_parallel(bench_prices[b], txn, daily, trading_days)
        for b in benchmarks
    }

    # ── 12. Capital flows ──────────────────────────────────────────────────
    cum_dep, cum_wd, net_inv = ts_mod.capital_flows(txn, daily, trading_days)

    # ── 13. Trim everything to first meaningful day ────────────────────────
    first_day = ts_mod.trim_to_first_meaningful_day(total_value_ts)
    mask = trading_days >= first_day

    total_plot = total_value_ts[mask]
    equity_plot = equity_ts[mask]
    cash_plot = cash_ts[mask]
    spy_plot = bench_value_ts[benchmarks[0]][mask]
    qqq_plot = bench_value_ts[benchmarks[1]][mask] if len(benchmarks) > 1 else pd.Series(dtype=float)
    cum_dep = cum_dep[mask]
    cum_wd = cum_wd[mask]
    net_inv = net_inv[mask]

    # ── 14. TWR ────────────────────────────────────────────────────────────
    twr_port = ret_mod.twr(total_value_ts, txn, trading_days, daily)[mask]
    twr_spy = ret_mod.benchmark_twr(bench_prices[benchmarks[0]], first_day)[mask]
    twr_qqq = (
        ret_mod.benchmark_twr(bench_prices[benchmarks[1]], first_day)[mask]
        if len(benchmarks) > 1
        else pd.Series(dtype=float)
    )

    return PortfolioSnapshot(
        open_positions=open_pos,
        pnl=pnl,
        realized=realized,
        realized_summary=realized_summary,
        free_cash=fc,
        portfolio_value_ts=total_plot,
        portfolio_equity_ts=equity_plot,
        cash_ts=cash_plot,
        spy_ts=spy_plot,
        qqq_ts=qqq_plot,
        cumulative_deposits=cum_dep,
        cumulative_withdrawals=cum_wd,
        net_invested=net_inv,
        twr_portfolio=twr_port,
        twr_spy=twr_spy,
        twr_qqq=twr_qqq,
        max_drawdown_portfolio=risk_mod.max_drawdown(twr_port),
        max_drawdown_spy=risk_mod.max_drawdown(twr_spy),
        max_drawdown_qqq=risk_mod.max_drawdown(twr_qqq) if len(twr_qqq) else 0.0,
        sharpe_portfolio=risk_mod.sharpe(twr_port),
        sharpe_spy=risk_mod.sharpe(twr_spy),
        sharpe_qqq=risk_mod.sharpe(twr_qqq) if len(twr_qqq) else 0.0,
        monthly_deposits=_current_month_deposits(txn),
        last_txn_date=_last_txn_date(txn),
        last_updated=pd.Timestamp.now(),
    )
