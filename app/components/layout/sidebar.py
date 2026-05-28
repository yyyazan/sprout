"""Vertical sidebar — nav links with active-state highlight."""
from __future__ import annotations

from dash import ALL, Input, Output, callback, dcc, html
from dash_iconify import DashIconify

NAV = [
    ("Dashboard",   "/",            "tabler:layout-dashboard"),
    ("Investments", "/investments", "tabler:trending-up"),
    ("Log",         "/trades",      "tabler:history"),
]


def sidebar() -> html.Aside:
    items = [
        dcc.Link(
            html.Div(
                [
                    DashIconify(icon=icon, width=18, className="nav-icon"),
                    html.Span(label, className="nav-label"),
                ],
                className="nav-item",
            ),
            href=path,
            id={"type": "nav-link", "path": path},
            className="nav-link",
        )
        for label, path, icon in NAV
    ]
    return html.Aside(
        [
            html.Div([html.H1("portfolio", className="brand-title")], className="brand"),
            html.Nav(items, className="nav"),
        ],
        className="sidebar",
    )


def _is_active(pathname: str | None, path: str) -> bool:
    if not pathname:
        return path == "/"
    if path == "/":
        return pathname == "/"
    return pathname == path or pathname.startswith(path + "/")


@callback(
    Output({"type": "nav-link", "path": ALL}, "className"),
    Input("url", "pathname"),
)
def _highlight_active(pathname):
    return [
        "nav-link active" if _is_active(pathname, path) else "nav-link"
        for _, path, _ in NAV
    ]
