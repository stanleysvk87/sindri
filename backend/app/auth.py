import hashlib
import hmac
import ipaddress
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
# "IP" means whatever client_ip() resolves to -- behind a reverse proxy
# that is only the real client when SINDRI_TRUSTED_PROXIES names the
# proxy, see client_ip's docstring.
LOGIN_ATTEMPT_WINDOW = timedelta(minutes=15)
LOGIN_ATTEMPT_MAX = 5


def cookie_secure() -> bool:
    """`secure` on the session cookie. Off by default because the
    documented deployment is plain HTTP on a LAN (a secure cookie would
    simply never be sent there, breaking login). Set
    SINDRI_COOKIE_SECURE=true when the app sits behind HTTPS."""
    return os.environ.get("SINDRI_COOKIE_SECURE", "false").lower() == "true"


def _trusted_proxies() -> list:
    """Peers whose X-Forwarded-For / X-Real-IP header may be believed.
    Entries are IPs, CIDR networks, or (for tests/socket-ish peers) plain
    strings matched exactly. Empty = trust nothing, which is the safe
    default for a backend reached directly."""
    raw = os.environ.get("SINDRI_TRUSTED_PROXIES", "")
    entries = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            entries.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            entries.append(item)
    return entries


def _is_trusted_proxy(peer: str) -> bool:
    if not peer:
        return False
    entries = _trusted_proxies()
    if "*" in entries:
        return True
    try:
        peer_ip = ipaddress.ip_address(peer)
    except ValueError:
        peer_ip = None
    for entry in entries:
        if isinstance(entry, str):
            if entry == peer:
                return True
        elif peer_ip is not None and peer_ip in entry:
            return True
    return False


def client_ip(request: Request) -> str:
    """The address the lockout counter is keyed on.

    Behind the bundled nginx container every request arrives from the
    proxy's own container IP, so keying on request.client.host alone made
    the "per-IP" lockout global: any one client on the LAN could burn 5
    wrong passwords and lock the owner out of every device. The forwarded
    header fixes that -- but only when the direct peer is a proxy we were
    explicitly told to trust (SINDRI_TRUSTED_PROXIES), otherwise anyone
    could just send X-Real-IP themselves and never be locked out at all.
    """
    peer = request.client.host if request.client else ""
    if _is_trusted_proxy(peer):
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            # Left-most entry is the original client; intermediate hops
            # append themselves on the right.
            candidate = forwarded.split(",")[0].strip()
            if candidate:
                return candidate
        real_ip = request.headers.get("x-real-ip", "").strip()
        if real_ip:
            return real_ip
    return peer or "unknown"


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
    """Changing the password invalidates every existing session. Without
    this, noticing a stolen session cookie and changing the password did
    nothing at all -- the stolen token stayed valid for the rest of its
    14-day TTL. The caller is expected to mint a fresh session for
    whoever performed the change (see routes_settings.update_account_password)."""
    set_setting("app_password_hash", _hash_password(new_password))
    delete_all_sessions()


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


def delete_session(token: str | None) -> None:
    """Server-side logout. Deleting the cookie client-side alone left the
    token valid, so anyone who had copied it stayed logged in."""
    if not token:
        return
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def delete_all_sessions() -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions")


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
