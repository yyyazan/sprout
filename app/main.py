"""Dash entry point — multi-page, BasicAuth, snapshot-at-boot.

Exports `server` for gunicorn (`gunicorn app.main:server`).
"""
from __future__ import annotations

import bcrypt
import dash
import dash_auth
import dash_mantine_components as dmc
from dash import dcc, html

from app import config
from app.state import get_snapshot

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    suppress_callback_exceptions=True,
    title="Portfolio",
    update_title=None,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1, viewport-fit=cover"},
        {"name": "theme-color", "content": "#000000"},
        {"name": "apple-mobile-web-app-capable", "content": "yes"},
        {"name": "apple-mobile-web-app-status-bar-style", "content": "black-translucent"},
    ],
)
server = app.server


@server.route("/healthz")
def healthz():
    return "ok", 200


def _verify(user: str, pw: str) -> bool:
    if not config.AUTH_ENABLED:
        return True
    if user != config.DASH_AUTH_USER:
        return False
    try:
        return bcrypt.checkpw(pw.encode(), config.DASH_AUTH_PASS_BCRYPT.encode())
    except Exception:
        return False


if config.AUTH_ENABLED:
    dash_auth.BasicAuth(app, auth_func=_verify, public_routes=["/healthz"])


# Warm the snapshot at boot so the first request doesn't pay yfinance latency.
# Wrapped in try so a missing data file doesn't crash the server — pages will
# show the error and let auth still gate the rest.
try:
    get_snapshot()
except Exception as exc:  # pragma: no cover
    print(f"[boot] snapshot warm failed: {exc!r}")


app.layout = dmc.MantineProvider(
    forceColorScheme="light",
    children=[
        dcc.Location(id="url"),
        dash.page_container,
    ],
)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
