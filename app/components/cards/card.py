"""Frosted-glass container — the visual primitive used everywhere.

Pass `size` to opt into the widget-grid sizing system (see `.widget-*` rules
in `app.css`). Sizes follow Apple's widget proportions:

    small   1×1 square
    medium  2×1 horizontal
    large   2×2 big square
    xl      4×2 banner
    tall    2×3 vertical

Without `size`, behaves as a plain card.
"""
from __future__ import annotations

from dash import html


def card(*children, size: str | None = None, className: str = "", **kwargs) -> html.Div:
    classes = ["glass-card"]
    if size:
        classes.append(f"widget widget-{size}")
    if className:
        classes.append(className)
    return html.Div(list(children), className=" ".join(classes), **kwargs)
