"""KPI card — label, formatted value, optional delta, optional subtitle."""
from __future__ import annotations

from dash import html

from app.components.cards.card import card


def _format_value(value, kind: str) -> str:
    if value is None:
        return "—"
    if kind == "money":
        return f"${value:,.2f}"
    if kind == "money_compact":
        sign = "+" if value > 0 else ""
        return f"{sign}${value:,.0f}"
    if kind == "percent":
        sign = "+" if value > 0 else ""
        return f"{sign}{value * 100:.2f}%"
    if kind == "ratio":
        return f"{value:.2f}"
    return str(value)


def kpi_card(
    label: str,
    value,
    kind: str = "money",
    delta=None,
    delta_kind: str = "percent",
    *,
    subtitle: str | None = None,
    size: str | None = None,
):
    if delta is None:
        delta_node = html.Div()
    else:
        cls = "kpi-delta-up" if delta >= 0 else "kpi-delta-down"
        delta_node = html.Span(_format_value(delta, delta_kind), className=f"kpi-delta {cls}")

    value_class = "kpi-value"
    if kind in ("money_compact", "percent") and value is not None:
        value_class += " kpi-value-up" if value >= 0 else " kpi-value-down"

    return card(
        html.Div(label, className="kpi-label"),
        html.Div(_format_value(value, kind), className=value_class),
        delta_node,
        html.Div(subtitle, className="kpi-subtitle") if subtitle else html.Div(),
        size=size,
        className="kpi-card",
    )
