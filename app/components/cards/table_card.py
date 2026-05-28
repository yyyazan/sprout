"""Table card — title header + a DataTable (or any body) wrapped in glass.

Also exports `TABLE_STYLE`: the mono/transparent style block used by every
DataTable in the app. Unpack it into the DataTable constructor.
"""
from __future__ import annotations

from dash import html

from app.components.cards.card import card


TABLE_STYLE = {
    "style_as_list_view": True,
    "style_table": {"overflowX": "auto"},
    "style_header": {
        "backgroundColor": "transparent",
        "color": "var(--muted)",
        "fontFamily": "ui-monospace, monospace",
        "fontSize": "11px",
        "textTransform": "uppercase",
        "letterSpacing": "0.08em",
        "borderBottom": "1px solid var(--border)",
    },
    "style_cell": {
        "backgroundColor": "transparent",
        "color": "var(--text)",
        "fontFamily": "ui-monospace, monospace",
        "fontSize": "13px",
        "padding": "10px 14px",
        "border": "none",
        "borderBottom": "1px solid var(--border)",
    },
}


def align_columns(columns: list[dict]) -> list[dict]:
    """Left-align text columns, right-align numeric ones.

    Dash DataTable right-aligns every cell by default, which looks adrift when
    text columns are wide. Pass the result as `style_cell_conditional`.
    """
    return [
        {
            "if": {"column_id": c["id"]},
            "textAlign": "right" if c.get("type") == "numeric" else "left",
        }
        for c in columns
    ]


def table_card(title: str, body) -> html.Div:
    return card(
        html.Div(html.H3(title, className="chart-title"), className="chart-head"),
        body,
        className="table-card",
    )
