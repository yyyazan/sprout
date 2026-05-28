"""Dashboard.

Goal: open on phone, scan in 2 minutes, close. Anything analytical lives in
the Investments tab. Anything entry-related lives in the Log tab.
"""
from __future__ import annotations

import dash
import pandas as pd

from app.components.cards.allocation_panel import allocation_panel
from app.components.cards.chart_card import chart_card
from app.components.cards.kpi_card import kpi_card
from app.components.cards.progress_card import progress_card
from app.components.layout.page_shell import page_shell
from app.components.layout.widget_grid import widget_grid
from app.config import MONTHLY_SAVINGS_TARGET
from app.state import get_snapshot
from portfolio.viz import figures

dash.register_page(__name__, path="/", name="Dashboard", order=0)


def _last(series: pd.Series, default=None):
    return float(series.iloc[-1]) if len(series) else default


def layout():
    s = get_snapshot()

    portfolio_value = _last(s.portfolio_value_ts, default=float(s.free_cash))
    total_pnl = float(s.pnl["unrealized_pnl"].sum()) + float(s.realized_summary.sum())

    you_pct = _last(s.twr_portfolio)
    spy_pct = _last(s.twr_spy)
    spy_delta = (you_pct - spy_pct) if (you_pct is not None and spy_pct is not None) else None

    last_txn = s.last_txn_date.strftime("%Y-%m-%d") if s.last_txn_date is not None else "—"

    tiles = widget_grid(
        # Row 1: cluster top (Cash, S&P δ) + Portfolio Value hero + Allocation panel starts.
        kpi_card("Cash", s.free_cash, kind="money", size="small", subtitle="available · incl. manual reconciliation offset"),
        kpi_card("S&P500 delta", spy_delta, kind="percent", size="small", subtitle="since inception"),
        kpi_card("Portfolio Value", portfolio_value, kind="money", size="medium", subtitle="equity + cash"),
        allocation_panel(s.pnl["market_value"], cash=max(s.free_cash, 0), size="tall"),

        # Row 2: goal long-rect (completes cluster) + Total P&L hero.
        progress_card("goal", s.monthly_deposits, MONTHLY_SAVINGS_TARGET, size="medium"),
        kpi_card("Total P&L", total_pnl, kind="money_compact", size="medium", subtitle="unrealized + realized"),

        # Rows 3-4: Portfolio Value chart spans the full bottom (xl = 4×2).
        chart_card("Portfolio Value", figures.equity_curve(s.portfolio_value_ts), size="xl"),
    )
    return page_shell(title="Dashboard", subtitle=f"last updated {last_txn}", content=tiles)
