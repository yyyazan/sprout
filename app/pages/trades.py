"""Log — audit mode. Entry form first, then trade log + realized P&L.

Reading order:
  1. layout()                  — what the page is
  2. _manage_card              — tabbed entry form (trades / transactions)
  3. _trades_panel / _txn_panel — the two tabs
  4. _logs_card                — toggled trade-record / transaction tables
  5. _realized_table           — full FIFO realized history
  6. Validation                — pure functions, no Dash
  7. Callbacks                 — small UI reactions, then save
"""
from __future__ import annotations

import re
from datetime import date, datetime

import dash
import dash_mantine_components as dmc
import pandas as pd
from dash import Input, Output, State, callback, dash_table, html, no_update

from app.components.cards.card import card
from app.components.cards.table_card import TABLE_STYLE, align_columns, table_card
from app.components.layout.page_shell import page_shell
from app.config import DATA_DIR
from app.state import get_snapshot, refresh
from portfolio.data import loader, writer

dash.register_page(__name__, path="/trades", name="Log", order=2)

TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
TRADES_PATH = DATA_DIR / "trades.csv"
TXN_PATH = DATA_DIR / "transactions.csv"

ACTION_DATA = [{"value": "buy", "label": "Buy"}, {"value": "sell", "label": "Sell"}]
TXN_TYPES = ["Deposit", "Withdrawal"]


def _txn_direction(amount: float) -> str:
    """Transaction type is not stored — it's inferred from the sign of the amount."""
    return "Deposit" if amount >= 0 else "Withdrawal"

LABEL_STYLE = {
    "fontSize": "12px",
    "color": "var(--muted)",
    "letterSpacing": "0.06em",
}


# ── Page layout ────────────────────────────────────────────────────────────────

def layout():
    return page_shell(
        title="Log",
        content=[
            _manage_card(),
            _logs_card(),
            _realized_table(),
        ],
    )


# ── Manage card (tabbed entry forms) ───────────────────────────────────────────

def _manage_card() -> html.Div:
    return card(
        dmc.Stack(
            [
                dmc.Center(
                    dmc.SegmentedControl(
                        id="manage-switch",
                        value="trades",
                        data=[
                            {"value": "trades", "label": "Trades"},
                            {"value": "txn", "label": "Transactions"},
                        ],
                        radius="xl",
                        size="md",
                        transitionDuration=250,
                        className="manage-switch",
                    )
                ),
                html.Div(_trades_panel(), id="panel-trades"),
                html.Div(_txn_panel(), id="panel-txn", style={"display": "none"}),
            ],
            gap="lg",
        )
    )


# Both forms share one column layout so the controls common to each
# (date · slider · numeric) sit in the same place. Trades fills the third slot
# with Ticker; transactions leave it blank.
_TICKER_W = 120


def _entry_row(*, date_node, slider, ticker_node, numeric) -> dmc.Group:
    return dmc.Group([date_node, slider, ticker_node, numeric], align="end", gap="sm")


def _trades_panel() -> dmc.Stack:
    today = date.today().isoformat()
    row = _entry_row(
        date_node=_date_with_today("trade-date", "trade-today", default=today),
        slider=dmc.SegmentedControl(
            id="trade-action",
            data=ACTION_DATA,
            value="buy",
            color="teal",
            transitionDuration=150,
            w=150,
        ),
        ticker_node=dmc.TextInput(
            id="trade-ticker",
            label="Ticker",
            placeholder="AAPL",
            w=_TICKER_W,
            styles={"input": {"textTransform": "uppercase"}},
        ),
        numeric=dmc.NumberInput(
            id="trade-shares",
            label="Shares",
            placeholder="1.5",
            decimalScale=6,
            min=0,
            hideControls=True,
            w=140,
        ),
    )
    return dmc.Stack(
        [
            row,
            _save_row("Save", "trade-submit", "trade-feedback"),
            _recent_block("trade", _recent_trades()),
        ],
        gap="md",
    )


def _txn_panel() -> dmc.Stack:
    today = date.today().isoformat()
    row = _entry_row(
        date_node=_date_with_today("txn-date", "txn-today", default=today),
        slider=dmc.SegmentedControl(
            id="txn-type",
            data=[{"value": t, "label": t} for t in TXN_TYPES],
            value="Deposit",
            color="teal",
            transitionDuration=150,
            w=150,
        ),
        ticker_node=html.Div(style={"width": _TICKER_W}),
        numeric=dmc.NumberInput(
            id="txn-amount",
            label="Amount",
            placeholder="500.00",
            prefix="$ ",
            decimalScale=2,
            min=0,
            hideControls=True,
            w=140,
        ),
    )
    return dmc.Stack(
        [
            row,
            _save_row("Save", "txn-submit", "txn-feedback"),
            _recent_block("txn", _recent_txns()),
        ],
        gap="md",
    )


def _date_with_today(date_id: str, today_id: str, *, default: str) -> dmc.Group:
    return dmc.Group(
        [
            dmc.DateInput(
                id=date_id,
                label="Date",
                value=default,
                maxDate=default,
                valueFormat="YYYY-MM-DD",
                w=150,
            ),
            dmc.Button("Today", id=today_id, variant="subtle", size="compact-xs"),
        ],
        gap=4,
        align="end",
    )


def _save_row(label: str, button_id: str, feedback_id: str) -> dmc.Group:
    return dmc.Group(
        [
            dmc.Button(label, id=button_id, color="dark"),
            html.Div(id=feedback_id, style={"flex": 1}),
        ],
        gap="sm",
    )


# ── Recent (collapsible per tab) ───────────────────────────────────────────────

def _recent_block(kind: str, initial_content: html.Div) -> html.Div:
    return html.Div(
        [
            dmc.UnstyledButton(
                [
                    dmc.Text("Recent", style=LABEL_STYLE),
                    dmc.Text("▾", id=f"{kind}-recent-caret", style={"marginLeft": 6, "color": "var(--muted)"}),
                ],
                id=f"{kind}-recent-toggle",
                style={"display": "inline-flex", "alignItems": "center", "padding": "4px 0"},
            ),
            dmc.Collapse(
                html.Div(initial_content, id=f"{kind}-recent-content", style={"paddingTop": 8}),
                id=f"{kind}-recent-collapse",
                opened=False,
            ),
        ]
    )


def _recent_table(df: pd.DataFrame, columns: list[tuple[str, str]]) -> html.Div:
    if df.empty:
        return html.Div("No entries yet.", style={"color": "var(--muted)", "fontSize": "12px"})
    th_style = {**LABEL_STYLE, "textAlign": "left", "padding": "6px 8px", "fontSize": "11px"}
    td_style = {"padding": "6px 8px", "fontSize": "13px", "borderTop": "1px solid var(--border)"}
    head = html.Thead(html.Tr([html.Th(label, style=th_style) for _, label in columns]))
    body = html.Tbody(
        [
            html.Tr([html.Td(str(row[col]), style=td_style) for col, _ in columns])
            for _, row in df.iterrows()
        ]
    )
    return html.Table([head, body], style={"width": "100%", "borderCollapse": "collapse"})


def _recent_trades() -> html.Div:
    if not TRADES_PATH.exists():
        return _recent_table(pd.DataFrame(), [])
    df = loader.load_trades(TRADES_PATH).tail(5).iloc[::-1].copy()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return _recent_table(
        df[["date", "ticker", "action", "shares"]],
        [("date", "Date"), ("ticker", "Ticker"), ("action", "Action"), ("shares", "Shares")],
    )


def _recent_txns() -> html.Div:
    if not TXN_PATH.exists():
        return _recent_table(pd.DataFrame(), [])
    df = loader.load_transactions(TXN_PATH).tail(5).iloc[::-1].copy()
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    df["Type"] = df["Amount (USD)"].map(_txn_direction)
    df["Amount (USD)"] = df["Amount (USD)"].map(lambda v: f"${v:,.2f}")
    return _recent_table(
        df[["Date", "Type", "Amount (USD)"]],
        [("Date", "Date"), ("Type", "Type"), ("Amount (USD)", "Amount")],
    )


# ── History tables (trade record, realized P&L, transactions) ──────────────────

def _empty_note(text: str) -> html.Div:
    return html.Div(text, style={"color": "var(--muted)", "fontSize": "13px", "padding": "8px 4px"})


# The Trades / Transactions logs share one card; a segmented control swaps the
# two table bodies (mirrors the `manage-switch` pattern on the entry forms).

def _logs_card() -> html.Div:
    return card(
        dmc.Stack(
            [
                dmc.Center(
                    dmc.SegmentedControl(
                        id="logs-switch",
                        value="trades",
                        data=[
                            {"value": "trades", "label": "Trades"},
                            {"value": "txn", "label": "Transactions"},
                        ],
                        radius="xl",
                        size="md",
                        transitionDuration=250,
                        className="manage-switch",
                    )
                ),
                html.Div(_trade_record_body(), id="log-panel-trades"),
                html.Div(_txn_log_body(), id="log-panel-txn", style={"display": "none"}),
            ],
            gap="lg",
        ),
        className="table-card",
    )


def _trade_record_body():
    if not TRADES_PATH.exists():
        return _empty_note("No trades yet.")

    df = loader.load_trades(TRADES_PATH).copy()
    df = df.sort_values("date", ascending=False)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df["action"] = df["action"].str.title()

    columns = [
        {"name": "Date", "id": "date"},
        {"name": "Ticker", "id": "ticker"},
        {"name": "Action", "id": "action"},
        {"name": "Shares", "id": "shares", "type": "numeric", "format": {"specifier": ",.4f"}},
    ]
    return dash_table.DataTable(
        data=df[["date", "ticker", "action", "shares"]].to_dict("records"),
        columns=columns,
        sort_action="native",
        page_size=25,
        **TABLE_STYLE,
        style_cell_conditional=align_columns(columns),
        style_data_conditional=[
            {"if": {"filter_query": '{action} = "Buy"', "column_id": "action"}, "color": "var(--gain)"},
            {"if": {"filter_query": '{action} = "Sell"', "column_id": "action"}, "color": "var(--loss)"},
        ],
    )


def _realized_table() -> html.Div:
    s = get_snapshot()
    realized = s.realized.copy() if not s.realized.empty else None

    if realized is None or realized.empty:
        return table_card("Realized P&L (FIFO)", _empty_note("No realized matches yet."))

    realized = realized.sort_values("sell_date", ascending=False)
    realized["buy_date"] = realized["buy_date"].dt.strftime("%Y-%m-%d")
    realized["sell_date"] = realized["sell_date"].dt.strftime("%Y-%m-%d")

    columns = [
        {"name": "Sell Date", "id": "sell_date"},
        {"name": "Ticker", "id": "ticker"},
        {"name": "Shares", "id": "shares", "type": "numeric", "format": {"specifier": ",.4f"}},
        {"name": "Buy Date", "id": "buy_date"},
        {"name": "Buy Price", "id": "buy_price", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Sell Price", "id": "sell_price", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Realized P&L", "id": "realized_pnl", "type": "numeric", "format": {"specifier": "+$,.2f"}},
    ]
    return table_card(
        "Realized P&L (FIFO)",
        dash_table.DataTable(
            data=realized.to_dict("records"),
            columns=columns,
            sort_action="native",
            page_size=25,
            **TABLE_STYLE,
            style_cell_conditional=align_columns(columns),
            style_data_conditional=[
                {"if": {"filter_query": "{realized_pnl} >= 0", "column_id": "realized_pnl"}, "color": "var(--gain)"},
                {"if": {"filter_query": "{realized_pnl} < 0", "column_id": "realized_pnl"}, "color": "var(--loss)"},
            ],
        ),
    )


def _txn_log_body():
    if not TXN_PATH.exists():
        return _empty_note("No transactions yet.")

    df = loader.load_transactions(TXN_PATH).copy()
    df = df.sort_values("Date", ascending=False)
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    df["Type"] = df["Amount (USD)"].map(_txn_direction)

    columns = [
        {"name": "Date", "id": "Date"},
        {"name": "Type", "id": "Type"},
        {"name": "Amount", "id": "Amount (USD)", "type": "numeric", "format": {"specifier": "+$,.2f"}},
    ]
    return dash_table.DataTable(
        data=df[["Date", "Type", "Amount (USD)"]].to_dict("records"),
        columns=columns,
        sort_action="native",
        page_size=25,
        **TABLE_STYLE,
        style_cell_conditional=align_columns(columns),
        style_data_conditional=[
            {"if": {"filter_query": "{Amount (USD)} >= 0", "column_id": "Amount (USD)"}, "color": "var(--gain)"},
            {"if": {"filter_query": "{Amount (USD)} < 0", "column_id": "Amount (USD)"}, "color": "var(--loss)"},
        ],
    )


# ── Validation (pure functions — no Dash, easy to unit-test) ───────────────────

def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def _validate_trade(ticker, action, shares, trade_date) -> tuple[dict[str, str], dict]:
    errors: dict[str, str] = {}

    cleaned_ticker = str(ticker or "").strip().upper()
    if not cleaned_ticker:
        errors["ticker"] = "Required."
    elif not TICKER_RE.match(cleaned_ticker):
        errors["ticker"] = "Invalid format."

    if action not in {"buy", "sell"}:
        errors["action"] = "Pick Buy or Sell."

    try:
        shares_val = float(shares) if shares not in (None, "") else None
    except (TypeError, ValueError):
        shares_val = None
    if shares_val is None:
        errors["shares"] = "Required."
    elif shares_val <= 0:
        errors["shares"] = "Must be > 0."

    parsed = _parse_date(trade_date)
    if parsed is None:
        errors["date"] = "Invalid date."
    elif parsed > date.today():
        errors["date"] = "Cannot be future."

    if not errors and action == "sell":
        snap = get_snapshot()
        held = float(snap.open_positions.get(cleaned_ticker, 0.0)) if cleaned_ticker in snap.open_positions.index else 0.0
        if held <= 0:
            errors["ticker"] = f"No open position in {cleaned_ticker}."
        elif shares_val > held + 1e-6:
            errors["shares"] = f"Exceeds {held:.4f} held."

    if errors:
        return errors, {}
    return {}, {"ticker": cleaned_ticker, "action": action, "shares": shares_val, "trade_date": parsed}


def _validate_txn(txn_date, txn_type, amount) -> tuple[str | None, dict]:
    parsed = _parse_date(txn_date)
    if parsed is None:
        return "Date is invalid.", {}
    if parsed > date.today():
        return "Date cannot be in the future.", {}
    if txn_type not in TXN_TYPES:
        return "Type is invalid.", {}
    try:
        magnitude = float(amount) if amount not in (None, "") else None
    except (TypeError, ValueError):
        return "Amount must be a number.", {}
    if magnitude is None or magnitude <= 0:
        return "Amount must be greater than zero.", {}

    signed = magnitude if txn_type == "Deposit" else -magnitude
    return None, {"txn_date": parsed, "txn_type": txn_type, "amount": signed}


# ── Feedback alerts ────────────────────────────────────────────────────────────

def _success(message: str) -> dmc.Alert:
    return dmc.Alert(f"✓ {message}", color="teal", variant="light", withCloseButton=False)


def _error(message: str) -> dmc.Alert:
    return dmc.Alert(message, color="red", variant="light", withCloseButton=False)


# ── Callbacks: small UI reactions ──────────────────────────────────────────────

@callback(
    Output("panel-trades", "style"),
    Output("panel-txn", "style"),
    Input("manage-switch", "value"),
)
def _switch_panel(value):
    on, off = {"display": "block"}, {"display": "none"}
    return (on, off) if value == "trades" else (off, on)


@callback(
    Output("log-panel-trades", "style"),
    Output("log-panel-txn", "style"),
    Input("logs-switch", "value"),
)
def _switch_log_panel(value):
    on, off = {"display": "block"}, {"display": "none"}
    return (on, off) if value == "trades" else (off, on)


@callback(Output("trade-action", "color"), Input("trade-action", "value"))
def _action_color(value):
    return "red" if value == "sell" else "teal"


@callback(Output("txn-type", "color"), Input("txn-type", "value"))
def _txn_type_color(value):
    return "red" if value == "Withdrawal" else "teal"


@callback(
    Output("trade-date", "value", allow_duplicate=True),
    Input("trade-today", "n_clicks"),
    prevent_initial_call=True,
)
def _trade_today(_):
    return date.today().isoformat()


@callback(
    Output("txn-date", "value", allow_duplicate=True),
    Input("txn-today", "n_clicks"),
    prevent_initial_call=True,
)
def _txn_today(_):
    return date.today().isoformat()


@callback(
    Output("trade-recent-collapse", "opened"),
    Output("trade-recent-caret", "children"),
    Input("trade-recent-toggle", "n_clicks"),
    State("trade-recent-collapse", "opened"),
    prevent_initial_call=True,
)
def _toggle_trade_recent(_, opened):
    new = not opened
    return new, "▴" if new else "▾"


@callback(
    Output("txn-recent-collapse", "opened"),
    Output("txn-recent-caret", "children"),
    Input("txn-recent-toggle", "n_clicks"),
    State("txn-recent-collapse", "opened"),
    prevent_initial_call=True,
)
def _toggle_txn_recent(_, opened):
    new = not opened
    return new, "▴" if new else "▾"


# ── Callbacks: live per-field validation ───────────────────────────────────────

@callback(
    Output("trade-ticker", "error", allow_duplicate=True),
    Input("trade-ticker", "value"),
    prevent_initial_call=True,
)
def _live_validate_ticker(value):
    if not value:
        return ""
    return "" if TICKER_RE.match(str(value).strip().upper()) else "Invalid format."


@callback(
    Output("trade-shares", "error", allow_duplicate=True),
    Input("trade-shares", "value"),
    prevent_initial_call=True,
)
def _live_validate_shares(value):
    if value in (None, ""):
        return ""
    try:
        return "" if float(value) > 0 else "Must be > 0."
    except (TypeError, ValueError):
        return "Invalid number."


# ── Callbacks: save ────────────────────────────────────────────────────────────

@callback(
    Output("trade-feedback", "children"),
    Output("trade-recent-content", "children"),
    Output("trade-ticker", "value"),
    Output("trade-shares", "value"),
    Output("trade-ticker", "error"),
    Output("trade-shares", "error"),
    Output("trade-date", "error"),
    Input("trade-submit", "n_clicks"),
    State("trade-ticker", "value"),
    State("trade-action", "value"),
    State("trade-shares", "value"),
    State("trade-date", "value"),
    prevent_initial_call=True,
)
def _save_trade(_n, ticker, action, shares, trade_date):
    errors, payload = _validate_trade(ticker, action, shares, trade_date)

    feedback = no_update
    recent = no_update
    ticker_value = no_update
    shares_value = no_update
    ticker_err = errors.get("ticker", "")
    shares_err = errors.get("shares", "")
    date_err = errors.get("date", "")

    if not errors:
        try:
            writer.append_trade(TRADES_PATH, **payload)
            refresh()
            msg = f"{payload['action'].title()} {payload['shares']:g} {payload['ticker']} on {payload['trade_date']}."
            feedback = _success(msg)
            recent = _recent_trades()
            ticker_value, shares_value = "", None
        except Exception as exc:
            feedback = _error(f"Save failed: {exc!r}")

    return feedback, recent, ticker_value, shares_value, ticker_err, shares_err, date_err


@callback(
    Output("txn-feedback", "children"),
    Output("txn-recent-content", "children"),
    Output("txn-amount", "value"),
    Input("txn-submit", "n_clicks"),
    State("txn-date", "value"),
    State("txn-type", "value"),
    State("txn-amount", "value"),
    prevent_initial_call=True,
)
def _save_txn(_n, txn_date, txn_type, amount):
    err, payload = _validate_txn(txn_date, txn_type, amount)
    if err:
        return _error(err), no_update, no_update
    try:
        writer.append_transaction(TXN_PATH, txn_date=payload["txn_date"], amount=payload["amount"])
        refresh()
    except Exception as exc:
        return _error(f"Save failed: {exc!r}"), no_update, no_update

    sign = "+" if payload["amount"] >= 0 else "−"
    msg = f"{payload['txn_type']} {sign}${abs(payload['amount']):,.2f} on {payload['txn_date']}."
    return _success(msg), _recent_txns(), None
