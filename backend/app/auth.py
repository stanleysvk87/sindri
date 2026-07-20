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

# Login brute-force protection -- there's exactly one account, so a
# per-IP sliding window is enough (no per-user lockout to reason about).
# 5 wrong passwords in 15 minutes locks that IP out until the window
# rolls forward; a correct login clears the IP's history immediately.
LOGIN_ATTEMPT_WINDOW = timedelta(minutes=15)
LOGIN_ATTEMPT_MAX = 5


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
        # Opportunistic cleanup -- sessions are never otherwise deleted,
        # so without this the table grows forever. Piggybacks on every
        # login instead of needing a separate cron/timer.
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now.isoformat(),))
        conn.execute(
            "INSERT INTO sessions (token, created_at, expires_at) VALUES (?, ?, ?)",
            (token, now.isoformat(), expires.isoformat()),
        )
    return token


def is_locked_out(ip: str) -> bool:
    cutoff = (datetime.now(timezone.utc) - LOGIN_ATTEMPT_WINDOW).isoformat()
    with get_conn() as conn:
        # Anything older than the window is irrelevant to the lockout
        # decision anyway -- delete it here so the table can't grow
        # unbounded under a sustained attack that never logs in
        # successfully from any single IP (the only other cleanup
        # trigger).
        conn.execute("DELETE FROM login_attempts WHERE attempted_at < ?", (cutoff,))
        count = conn.execute(
            "SELECT COUNT(*) c FROM login_attempts WHERE ip = ? AND attempted_at > ?",
            (ip, cutoff),
        ).fetchone()["c"]
    return count >= LOGIN_ATTEMPT_MAX


def record_failed_login(ip: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO login_attempts (ip, attempted_at) VALUES (?, ?)",
            (ip, datetime.now(timezone.utc).isoformat()),
        )


def clear_failed_logins(ip: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM login_attempts WHERE ip = ?", (ip,))


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
