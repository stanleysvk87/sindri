import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

from app.db import get_conn
from app.settings_store import get_setting, set_setting

COOKIE_NAME = "sindri_session"
SESSION_TTL = timedelta(days=14)
PBKDF2_ITERATIONS = 200_000


def _env_password() -> str:
    pw = os.environ.get("SINDRI_PASSWORD", "")
    if not pw:
        raise RuntimeError(
            "SINDRI_PASSWORD is not set — refusing to start with no auth password"
        )
    return pw


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}:{digest.hex()}"


def _verify_hash(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    candidate = _hash_password(password, salt)
    return hmac.compare_digest(candidate, f"{salt_hex}:{digest_hex}")


def check_password(candidate: str) -> bool:
    """A password changed via Settings (stored hashed, PBKDF2) always
    wins over SINDRI_PASSWORD -- the env var is only the bootstrap/
    default credential, same relationship as the AI settings override."""
    stored_hash = get_setting("app_password_hash")
    if stored_hash:
        return _verify_hash(candidate, stored_hash)
    return hmac.compare_digest(candidate, _env_password())


def set_password(new_password: str) -> None:
    set_setting("app_password_hash", _hash_password(new_password))


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
