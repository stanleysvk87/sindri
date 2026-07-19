import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

from app.db import get_conn

COOKIE_NAME = "sindri_session"
SESSION_TTL = timedelta(days=14)


def _password() -> str:
    pw = os.environ.get("SINDRI_PASSWORD", "")
    if not pw:
        raise RuntimeError(
            "SINDRI_PASSWORD is not set — refusing to start with no auth password"
        )
    return pw


def check_password(candidate: str) -> bool:
    return hmac.compare_digest(candidate, _password())


def create_session() -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + SESSION_TTL
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (token, created_at, expires_at) VALUES (?, ?, ?)",
            (token, now.isoformat(), expires.isoformat()),
        )
    return token


def session_valid(token: str | None) -> bool:
    if not token:
        return False
    with get_conn() as conn:
        row = conn.execute(
            "SELECT expires_at FROM sessions WHERE token = ?", (token,)
        ).fetchone()
    if not row:
        return False
    expires_at = datetime.fromisoformat(row["expires_at"])
    return datetime.now(timezone.utc) < expires_at


def require_auth(request: Request) -> None:
    token = request.cookies.get(COOKIE_NAME)
    if not session_valid(token):
        raise HTTPException(status_code=401, detail="Login required")
