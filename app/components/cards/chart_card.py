"""Chart card — title + plotly graph wrapped in glass.

The card's height comes from the widget tile (`size=`); the graph fills it.
"""
from __future__ import annotations

from dash import dcc, html

from app.components.cards.card import card


def chart_card(
    title: str,
    figure,
    *,
    size: str | None = None,
    subtitle: str | None = None,
):
    head = [html.H3(title, className="chart-title")]
    if subtitle:
        head.append(html.Span(subtitle, className="chart-subtitle"))

    return card(
        html.Div(head, className="chart-head"),
        dcc.Graph(
            figure=figure,
            config={"displayModeBar": False, "responsive": True},
            style={"height": "100%", "width": "100%", "flex": 1, "minHeight": 0},
        ),
        size=size,
        className="chart-card",
    )
