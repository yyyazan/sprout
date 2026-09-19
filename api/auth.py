"""Authentication — Google sign-in, with a password fallback for the owner.

Sprout is a personal app shared with a couple of friends, so identity is
deliberately small: sign in with Google, and the account is matched by Google's
stable subject id. Only addresses in ``SPROUT_ALLOWED_EMAILS`` may sign in —
without that, any Google account on earth could provision a portfolio here.

Sessions stay stateless (no session table): the cookie holds
``user_id.issued_at.hmac`` signed with ``SPROUT_SECRET``. That survives
restarts and lets a request resolve its user without a DB hit. Rotating the
secret revokes every outstanding session at once.

``SPROUT_PASSWORD`` is kept as an owner-only fallback so a broken OAuth config
(most likely a redirect-URI mismatch) can't lock the owner out of their own
portfolio.

Only ``/api/*`` is gated: the static SvelteKit shell holds no user data, and
serving it unauthenticated is what lets the frontend render the sign-in screen.
When neither a password nor a Google client is configured the gate is off
entirely — that's local dev.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
import urllib.parse

import requests
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse

from portfolio.data import db as db_mod

log = logging.getLogger("sprout.auth")

COOKIE_NAME = "sprout_session"
COOKIE_MAX_AGE = 90 * 24 * 3600  # ~3 months
STATE_COOKIE = "sprout_oauth_state"
STATE_MAX_AGE = 600  # the redirect to Google and back is a matter of seconds

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Last-resort signing key: only used when neither SPROUT_SECRET nor
# SPROUT_PASSWORD is set, which means sessions die on restart. Fine for dev,
# logged loudly because it would be a misconfiguration in production.
_EPHEMERAL_SECRET = secrets.token_hex(32)


# ── configuration ───────────────────────────────────────────────────────────


def _password() -> str:
    return os.environ.get("SPROUT_PASSWORD", "")


def _owner_email() -> str:
    return os.environ.get("SPROUT_OWNER_EMAIL", "").strip().lower()


def _allowed_emails() -> set[str]:
    raw = os.environ.get("SPROUT_ALLOWED_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def _google_client() -> tuple[str, str]:
    return (
        os.environ.get("GOOGLE_CLIENT_ID", ""),
        os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    )


def oauth_enabled() -> bool:
    cid, csecret = _google_client()
    return bool(cid and csecret)


def enabled() -> bool:
    """Whether the API gate is active at all (off = wide-open local dev)."""
    return bool(_password()) or oauth_enabled()


def startup_check() -> None:
    """Warn about the one misconfiguration that silently orphans real data.

    With Google sign-in on but no owner email, the owner's first sign-in mints a
    fresh account instead of claiming the pre-OAuth user_id=1 that holds the
    existing trade history — the portfolio just looks empty, with no error.
    """
    if oauth_enabled() and not _owner_email():
        log.warning(
            "GOOGLE_CLIENT_ID is set but SPROUT_OWNER_EMAIL is not — the first Google "
            "sign-in will create a NEW empty account instead of claiming user_id=%d, "
            "which owns the existing trade history.",
            db_mod.DEFAULT_USER_ID,
        )


def _secret() -> bytes:
    key = os.environ.get("SPROUT_SECRET") or _password()
    if not key:
        log.warning("no SPROUT_SECRET or SPROUT_PASSWORD set; sessions won't survive restart")
        key = _EPHEMERAL_SECRET
    return key.encode()


def _public_url(request: Request) -> str:
    """Origin to build the OAuth redirect URI from.

    Must match what's registered in the Google console byte-for-byte. Railway
    terminates TLS upstream, so the app sees plain http and request.url would
    produce an http:// URI that Google rejects — hence the explicit env var.
    """
    configured = os.environ.get("SPROUT_PUBLIC_URL", "").strip().rstrip("/")
    if configured:
        return configured
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    return f"{proto}://{request.headers.get('host', request.url.netloc)}"


def _redirect_uri(request: Request) -> str:
    return f"{_public_url(request)}/api/auth/google/callback"


# ── session tokens ──────────────────────────────────────────────────────────


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def _make_token(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time())}"
    return f"{payload}.{_sign(payload)}"


def _read_token(token: str) -> int | None:
    """Verify a session cookie and return its user_id, or None if it's not valid."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    user_id_s, issued_s, sig = parts
    if not hmac.compare_digest(sig, _sign(f"{user_id_s}.{issued_s}")):
        return None
    try:
        user_id, issued = int(user_id_s), int(issued_s)
    except ValueError:
        return None
    if time.time() - issued > COOKIE_MAX_AGE:
        return None
    return user_id


def session_user_id(request: Request) -> int | None:
    cookie = request.cookies.get(COOKIE_NAME, "")
    return _read_token(cookie) if cookie else None


def _cookie_secure(request: Request) -> bool:
    # Railway terminates TLS upstream; the app sees plain http with the proto
    # in x-forwarded-proto. Local dev is honest http and needs secure=False.
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


def _set_session(response: Response, request: Request, user_id: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        _make_token(user_id),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(request),
    )


# ── gate ────────────────────────────────────────────────────────────────────


class AuthGateMiddleware(BaseHTTPMiddleware):
    """401 every /api request without a valid session cookie.

    /api/auth/* stays open (it's how you get the cookie); everything else —
    static shell, /healthz — carries no portfolio data and passes through.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not enabled() or not path.startswith("/api") or path.startswith("/api/auth/"):
            return await call_next(request)
        if session_user_id(request) is not None:
            return await call_next(request)
        return JSONResponse({"detail": "locked"}, status_code=401)


def current_user_id(request: Request) -> int:
    """The identity a request is acting as.

    Routes take this via ``Depends`` rather than a plain ``user_id: int``
    default so it can't be overridden by a client-supplied query param
    (FastAPI treats a bare-int default as a query param; a Depends default
    isn't client-settable).
    """
    user_id = session_user_id(request)
    if user_id is not None:
        return user_id
    if not enabled():
        return db_mod.DEFAULT_USER_ID  # local dev, gate off
    raise HTTPException(status_code=401, detail="locked")


# ── password fallback (owner only) ──────────────────────────────────────────


def _owner_user_id() -> int:
    """Account the password fallback signs into — the owner's, else user 1."""
    email = _owner_email()
    if not email:
        return db_mod.DEFAULT_USER_ID
    conn = db_mod.connect()
    try:
        row = conn.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()
        return int(row["user_id"]) if row else db_mod.DEFAULT_USER_ID
    finally:
        conn.close()


class LoginIn(BaseModel):
    password: str


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    if not enabled():
        return {"ok": True}
    if not _password() or not hmac.compare_digest(
        (body.password or "").encode(), _password().encode()
    ):
        time.sleep(0.5)  # single worker — blunt but effective brute-force drag
        return JSONResponse({"ok": False}, status_code=401)
    _set_session(response, request, _owner_user_id())
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


# ── Google OAuth ────────────────────────────────────────────────────────────


@router.get("/google/login")
def google_login(request: Request):
    """Kick off the authorization-code flow."""
    if not oauth_enabled():
        raise HTTPException(status_code=404, detail="Google sign-in is not configured")
    client_id, _ = _google_client()
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": client_id,
        "redirect_uri": _redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    response = RedirectResponse(f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}")
    response.set_cookie(
        STATE_COOKIE,
        state,
        max_age=STATE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(request),
    )
    return response


def _fail(message: str) -> RedirectResponse:
    """Bounce back to the app with a reason the sign-in screen can render.

    The callback is a top-level browser navigation, so a raw JSON error would
    strand the user on a blank page.
    """
    return RedirectResponse(f"/?auth_error={urllib.parse.quote(message)}")


@router.get("/google/callback")
def google_callback(request: Request, code: str = "", state: str = ""):
    if not oauth_enabled():
        raise HTTPException(status_code=404, detail="Google sign-in is not configured")

    expected = request.cookies.get(STATE_COOKIE, "")
    if not state or not expected or not hmac.compare_digest(state, expected):
        return _fail("Sign-in expired. Please try again.")
    if not code:
        return _fail("Google did not return an authorization code.")

    client_id, client_secret = _google_client()
    try:
        token_res = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": _redirect_uri(request),
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_res.raise_for_status()
        access_token = token_res.json().get("access_token")
        if not access_token:
            return _fail("Google did not return an access token.")

        # The access token came straight from Google over TLS, so the userinfo
        # response is trusted without separately verifying an id_token JWT.
        info_res = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        info_res.raise_for_status()
        info = info_res.json()
    except requests.RequestException:
        log.exception("Google token exchange failed")
        return _fail("Could not reach Google. Please try again.")

    email = (info.get("email") or "").strip().lower()
    sub = info.get("sub") or ""
    if not email or not sub:
        return _fail("Google did not return an account email.")
    if not info.get("email_verified"):
        return _fail("That Google account's email isn't verified.")

    allowed = _allowed_emails()
    owner = _owner_email()
    if owner:
        allowed.add(owner)
    if not allowed:
        return _fail("No accounts are permitted yet. Set SPROUT_ALLOWED_EMAILS.")
    if email not in allowed:
        log.warning("rejected sign-in for %s (not on the allowlist)", email)
        return _fail(f"{email} isn't invited to this Sprout.")

    conn = db_mod.connect()
    try:
        user_id = db_mod.find_or_create_user(
            conn,
            google_sub=sub,
            email=email,
            display_name=info.get("name"),
            picture=info.get("picture"),
            owner_email=owner or None,
        )
    finally:
        conn.close()

    response = RedirectResponse("/")
    _set_session(response, request, user_id)
    response.delete_cookie(STATE_COOKIE)
    return response


@router.get("/me")
def me(request: Request):
    """Identity for the profile control. 401 when signed out."""
    user_id = session_user_id(request)
    if user_id is None:
        if not enabled():
            user_id = db_mod.DEFAULT_USER_ID  # local dev, gate off
        else:
            raise HTTPException(status_code=401, detail="locked")
    conn = db_mod.connect()
    try:
        row = db_mod.user_row(conn, user_id)
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="locked")
    return {
        "email": row["email"],
        "name": row["display_name"],
        "picture": row["picture"],
        "oauth": oauth_enabled(),
    }
