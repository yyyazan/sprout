"""Card hand — open positions rendered as a row of playing cards.

A light-faced playing-card hand sitting on a desaturated-green felt band. Each
position is a `.portfolio-card`; the final card is the Joker, carrying free
cash. Layout (left offsets, overlap) and ALL mouse interaction live in
`assets/cards.js` — this module only emits the static DOM + suit theming.

Each card is a stable, never-transformed `.portfolio-card` hit-wrapper holding
a `.card-inner` face. The pop/tilt/scale transform is applied to `.card-inner`
only, so the wrapper's hit area never moves — that's what keeps the hover from
jittering as the cursor crosses the tilting face.

The face shows identity and weight only (logo, ticker, name, position %). The
per-position detail (price, cost basis, vs-VOO, hold, value) is intentionally
NOT rendered yet — it will return later as a click-to-flip card back.
"""
from __future__ import annotations

from dash import dcc, html


def _corner(rank: str, symbol: str, cls: str) -> html.Div:
    return html.Div(
        [html.Span(rank, className="corner-rank"), html.Span(symbol, className="corner-suit")],
        className=f"corner {cls}",
    )


def _card(suit: str, index: int, inner_children: list) -> html.Div:
    return html.Div(
        html.Div(inner_children, className="card-inner"),
        className=f"portfolio-card suit-{suit}",
        **{"data-index": index, "data-suit": suit},
    )


def _position_card(c: dict, index: int) -> html.Div:
    rank, symbol = c["rank"], c["suit_symbol"]
    domain = c["domain"]

    logo_children = []
    if domain:
        logo_children.append(
            html.Img(
                src=f"https://icons.duckduckgo.com/ip3/{domain}.ico",
                className="card-logo",
                referrerPolicy="no-referrer",
            )
        )
    logo_children.append(
        html.Div(c["ticker"][:2].upper(), className="card-logo-fallback")
    )

    return _card(c["suit"], index, [
        _corner(rank, symbol, "corner-tl"),
        _corner(rank, symbol, "corner-br"),
        html.Div(
            [
                html.Div(logo_children, className="card-logo-wrap"),
                html.Div(c["ticker"], className="card-ticker"),
                html.Div(c["company_name"], className="card-name"),
                html.Div(f"{c['position_pct']:.1f}%", className="card-pct"),
                html.Div("of portfolio", className="card-pct-label"),
            ],
            className="card-center",
        ),
    ])


def _joker_card(c: dict, index: int) -> html.Div:
    word = html.Div([html.Span(ch) for ch in "JOKER"], className="joker-word")
    return _card("jk", index, [
        _corner("★", "", "corner-tl"),
        _corner("★", "", "corner-br"),
        html.Div(
            [
                html.Div("★", className="joker-star"),
                word,
                html.Div(f"${c['cash_usd']:,.2f}", className="card-pct"),
                html.Div("free cash", className="card-pct-label"),
            ],
            className="card-center joker-center",
        ),
    ])


def card_hand(cards: list[dict]) -> html.Div:
    children = [
        _joker_card(c, i) if c.get("is_joker") else _position_card(c, i)
        for i, c in enumerate(cards)
    ]
    return html.Div(
        [
            html.Div(children, className="card-hand", id="card-hand"),
            dcc.Store(id="card-hand-init"),
        ],
        className="card-hand-band",
    )
