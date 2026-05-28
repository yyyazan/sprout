"""Allocation panel — compact donut on top, ranked ticker list below.

Used as a side-rail widget on the dashboard.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html

from app.components.cards.card import card
from portfolio.viz.figures import PALETTE, PLOTLY_TEMPLATE


def _compact_donut(labels: list[str], values: list[float], colors: list[str]) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.62,
        marker=dict(colors=colors),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}  %{percent}<extra></extra>",
        showlegend=False,
        sort=False,
    ))
    fig.update_layout(template=PLOTLY_TEMPLATE, margin=dict(t=4, b=4, l=4, r=4))
    return fig


def allocation_panel(values: pd.Series, cash: float = 0.0, *, size: str = "tall"):
    series = values.copy()
    if cash > 0:
        series["Cash"] = cash
    series = series[series > 0].sort_values(ascending=False)

    labels = [str(i) for i in series.index]
    nums = [round(float(v), 2) for v in series.values]
    total = sum(nums) or 1.0
    colors = (PALETTE * (len(labels) // len(PALETTE) + 1))[: len(labels)]

    rows = [
        html.Div(
            [
                html.Span(className="alloc-dot", style={"backgroundColor": color}),
                html.Span(label, className="alloc-ticker"),
                html.Span(f"${value:,.0f}", className="alloc-amount"),
                html.Span(f"{value / total * 100:.1f}%", className="alloc-pct"),
            ],
            className="alloc-row",
        )
        for label, value, color in zip(labels, nums, colors)
    ]

    return card(
        html.Div("Allocation", className="alloc-panel-title"),
        dcc.Graph(
            figure=_compact_donut(labels, nums, colors),
            config={"displayModeBar": False, "responsive": True},
            className="alloc-donut",
            style={"height": "210px", "width": "100%"},
        ),
        html.Div(rows, className="alloc-list"),
        size=size,
        className="alloc-panel",
    )
