"""Progress card — label, $current / $target, percentage, and a green fill bar."""
from __future__ import annotations

from dash import html

from app.components.cards.card import card


def progress_card(label: str, current: float, target: float, *, size: str | None = None):
    pct = current / target if target > 0 else 0.0
    fill_width = f"{max(0.0, min(pct, 1.0)) * 100:.1f}%"
    return card(
        html.Div(label, className="kpi-label"),
        html.Div(f"${current:,.0f} / ${target:,.0f}", className="progress-value"),
        html.Div(html.Div(className="progress-fill", style={"width": fill_width}),
                 className="progress-bar"),
        html.Div(f"{pct * 100:.0f}%", className="progress-pct"),
        size=size,
        className="progress-card",
    )
