"""Widget grid — Apple-widget-style container for `size=`-aware cards.

Children should be cards built via `card`/`chart_card`/`kpi_card`/etc. with a
`size` prop ("small" / "medium" / "large" / "xl" / "tall"). The grid is 6 cols
on desktop and 2 on mobile; each size has a fixed aspect ratio that snaps to a
shared --unit, so tiles compose into clean rows automatically.
"""
from __future__ import annotations

from dash import html


def widget_grid(*children) -> html.Div:
    return html.Div(list(children), className="widget-grid")
