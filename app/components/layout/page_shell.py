"""App shell — wraps every page with header + sidebar + content slot."""
from __future__ import annotations

from dash import html

from app.components.layout.sidebar import sidebar


def page_shell(*, title: str, content, subtitle: str | None = None) -> html.Div:
    header_children = [html.H2(title, className="page-title")]
    if subtitle:
        header_children.append(html.Div(subtitle, className="page-subtitle"))
    return html.Div(
        [
            sidebar(),
            html.Main(
                [
                    html.Header(header_children, className="page-header"),
                    html.Div(content, className="page-content"),
                ],
                className="content",
            ),
        ],
        className="app-root",
    )
