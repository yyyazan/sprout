"""Plotly figure factories — minimal light theme to match the dashboard."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

ACCENT = "#e37961"   # coral, primary line
NEUTRAL = "#1c1c1e"  # near-black
MUTED = "#6b6b6f"
GRID = "#ececea"
GAIN = "#2f9e7d"
LOSS = "#c94f4f"
PALETTE = [ACCENT, "#2f9e7d", "#5b8def", "#c994e8", "#f0b86b", "#888888"]

PLOTLY_TEMPLATE: dict = {
    "layout": {
        "paper_bgcolor": "white",
        "plot_bgcolor": "white",
        "font": {"family": "-apple-system, system-ui, sans-serif", "color": NEUTRAL, "size": 12},
        "colorway": PALETTE,
        "xaxis": {"showgrid": True, "gridcolor": GRID, "zeroline": False, "linecolor": GRID, "tickfont": {"color": MUTED}},
        "yaxis": {"showgrid": True, "gridcolor": GRID, "zeroline": False, "linecolor": GRID, "tickfont": {"color": MUTED}},
        "margin": {"t": 20, "b": 30, "l": 50, "r": 20},
        "legend": {"font": {"color": NEUTRAL, "size": 11}, "bgcolor": "rgba(0,0,0,0)"},
    }
}


def _apply(fig: go.Figure) -> go.Figure:
    fig.update_layout(template=PLOTLY_TEMPLATE)
    return fig


def equity_curve(portfolio: pd.Series, benchmarks: dict[str, pd.Series] | None = None) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=portfolio.index, y=portfolio.round(2), mode="lines", name="Portfolio",
        line=dict(color=ACCENT, width=2),
        hovertemplate="<b>Portfolio</b>  %{x|%b %d %Y}<br>$%{y:,.2f}<extra></extra>",
    ))
    bench_colors = [MUTED, "#5b8def"]
    for (label, series), color in zip((benchmarks or {}).items(), bench_colors):
        fig.add_trace(go.Scatter(
            x=series.index, y=series.round(2), mode="lines", name=label,
            line=dict(color=color, width=1.4, dash="dot"),
            hovertemplate=f"<b>{label}</b>  %{{x|%b %d %Y}}<br>$%{{y:,.2f}}<extra></extra>",
        ))
    return _apply(fig)


def allocation_donut(values: pd.Series, cash: float = 0.0) -> go.Figure:
    labels = list(values.index) + (["Cash"] if cash > 0 else [])
    nums = list(values.round(2)) + ([round(cash, 2)] if cash > 0 else [])
    fig = go.Figure(go.Pie(
        labels=labels, values=nums, hole=0.6,
        marker=dict(colors=PALETTE * (len(labels) // len(PALETTE) + 1)),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}  %{percent}<extra></extra>",
    ))
    return _apply(fig)


def twr_vs_bench(portfolio_twr: pd.Series, benchmarks: dict[str, pd.Series]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=portfolio_twr.index, y=(portfolio_twr * 100).round(3), mode="lines", name="Portfolio",
        line=dict(color=ACCENT, width=2),
        hovertemplate="<b>Portfolio TWR</b>  %{x|%b %d %Y}<br>%{y:+.2f}%<extra></extra>",
    ))
    bench_colors = [MUTED, "#5b8def"]
    for (label, series), color in zip(benchmarks.items(), bench_colors):
        fig.add_trace(go.Scatter(
            x=series.index, y=(series * 100).round(3), mode="lines", name=label,
            line=dict(color=color, width=1.4, dash="dot"),
            hovertemplate=f"<b>{label} TWR</b>  %{{x|%b %d %Y}}<br>%{{y:+.2f}}%<extra></extra>",
        ))
    fig.add_hline(y=0, line_dash="dot", line_color=GRID)
    fig.update_yaxes(ticksuffix="%")
    return _apply(fig)


def drawdown_area(twr_series: pd.Series) -> go.Figure:
    equity = 1 + twr_series
    peak = equity.expanding().max()
    dd = (equity - peak) / peak * 100
    fig = go.Figure(go.Scatter(
        x=dd.index, y=dd.round(3), mode="lines",
        line=dict(color=LOSS, width=1.4),
        fill="tozeroy", fillcolor="rgba(201,79,79,0.12)",
        hovertemplate="<b>Drawdown</b>  %{x|%b %d %Y}<br>%{y:.2f}%<extra></extra>",
        name="Drawdown",
    ))
    fig.update_yaxes(ticksuffix="%")
    return _apply(fig)


def pnl_bars(pnl_by_ticker: pd.Series, label: str = "P&L") -> go.Figure:
    s = pnl_by_ticker.sort_values()
    colors = [GAIN if v >= 0 else LOSS for v in s]
    fig = go.Figure(go.Bar(
        y=s.index, x=s.values, orientation="h",
        marker_color=colors,
        text=[f"${v:+,.0f}" for v in s], textposition="outside",
        hovertemplate=f"<b>%{{y}}</b><br>{label}: $%{{x:+,.2f}}<extra></extra>",
        showlegend=False,
    ))
    return _apply(fig)
