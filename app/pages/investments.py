"""Investments — deep session view.

Consolidates positions, P&L, TWR, benchmark comparison, drawdown, allocation,
and per-ticker P&L breakdown.
"""
from __future__ import annotations

import dash
from dash import dash_table, html

from app.components.cards.chart_card import chart_card
from app.components.cards.kpi_card import kpi_card
from app.components.cards.table_card import TABLE_STYLE, table_card
from app.components.layout.page_shell import page_shell
from app.components.layout.widget_grid import widget_grid
from app.state import get_snapshot
from portfolio.viz import figures

dash.register_page(__name__, path="/investments", name="Investments", order=1)


def layout():
    s = get_snapshot()

    bench_twr = {"SPY": s.twr_spy}
    if not s.twr_qqq.empty:
        bench_twr["QQQ"] = s.twr_qqq

    twr_now = float(s.twr_portfolio.iloc[-1]) if len(s.twr_portfolio) else 0.0
    spy_now = float(s.twr_spy.iloc[-1]) if len(s.twr_spy) else 0.0

    tiles = widget_grid(
        kpi_card("TWR", twr_now, kind="percent", size="small"),
        kpi_card("Max Drawdown", s.max_drawdown_portfolio, kind="percent", size="small"),
        kpi_card("Sharpe", s.sharpe_portfolio, kind="ratio", size="small"),
        kpi_card("SPY TWR", spy_now, kind="percent", size="small"),
        kpi_card("SPY DD", s.max_drawdown_spy, kind="percent", size="small"),
        kpi_card("SPY Sharpe", s.sharpe_spy, kind="ratio", size="small"),
        chart_card(
            "Time-Weighted Return",
            figures.twr_vs_bench(s.twr_portfolio, bench_twr),
            size="large",
            subtitle="Strips out cash-flow timing — pure holding performance",
        ),
        chart_card("Drawdown", figures.drawdown_area(s.twr_portfolio), size="large"),
        chart_card(
            "Unrealized P&L by Ticker",
            figures.pnl_bars(s.pnl["unrealized_pnl"], "Unrealized P&L"),
            size="large",
        ),
        chart_card(
            "Allocation",
            figures.allocation_donut(s.pnl["market_value"], cash=max(s.free_cash, 0)),
            size="large",
        ),
    )

    return page_shell(title="Investments", content=[tiles, _positions_table(s)])


def _positions_table(s) -> html.Div:
    df = s.pnl.reset_index().rename(columns={"index": "ticker"})
    total_mv = float(df["market_value"].sum())
    df["weight"] = (df["market_value"] / total_mv * 100) if total_mv else 0.0

    columns = [
        {"name": "Ticker", "id": "ticker"},
        {"name": "Shares", "id": "shares", "type": "numeric", "format": {"specifier": ",.4f"}},
        {"name": "Cost Basis", "id": "cost_basis", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Current Price", "id": "current_price", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Invested", "id": "total_invested", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Market Value", "id": "market_value", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Unrealized $", "id": "unrealized_pnl", "type": "numeric", "format": {"specifier": "+$,.2f"}},
        {"name": "Return %", "id": "return_pct", "type": "numeric", "format": {"specifier": "+.2f"}},
        {"name": "Weight %", "id": "weight", "type": "numeric", "format": {"specifier": ".1f"}},
    ]

    return table_card(
        "Positions",
        dash_table.DataTable(
            data=df.to_dict("records"),
            columns=columns,
            sort_action="native",
            **TABLE_STYLE,
            style_data_conditional=[
                {"if": {"filter_query": "{unrealized_pnl} >= 0", "column_id": "unrealized_pnl"},
                 "color": "var(--gain)"},
                {"if": {"filter_query": "{unrealized_pnl} < 0", "column_id": "unrealized_pnl"},
                 "color": "var(--loss)"},
                {"if": {"filter_query": "{return_pct} >= 0", "column_id": "return_pct"},
                 "color": "var(--gain)"},
                {"if": {"filter_query": "{return_pct} < 0", "column_id": "return_pct"},
                 "color": "var(--loss)"},
            ],
        ),
    )
