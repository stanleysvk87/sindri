from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.auth import (
    COOKIE_NAME,
    check_password,
    clear_failed_logins,
    client_ip,
    cookie_secure,
    create_session,
    delete_session,
    is_locked_out,
    record_failed_login,
    require_auth,
)
from app.models import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response):
    # See auth.client_ip: behind the bundled nginx this is the real
    # client only when SINDRI_TRUSTED_PROXIES names the proxy.
    ip = client_ip(request)
    if is_locked_out(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts -- try again in a few minutes.",
        )

    if not check_password(payload.password):
        record_failed_login(ip)
        raise HTTPException(status_code=401, detail="Wrong password")

    clear_failed_logins(ip)
    token = create_session()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=cookie_secure(),
        max_age=14 * 24 * 3600,
    )
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response):
    # Drop the server-side session too, not just the browser's copy of
    # the cookie -- otherwise the token stays usable by anyone who has it.
    delete_session(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.post("/verify", dependencies=[Depends(require_auth)])
def verify(payload: LoginRequest):
    """Re-check the password without touching the session -- used to
    gate revealing a masked secret in the UI. Requires an already-valid
    session too, so this can't be used as a bare password-guessing
    oracle by someone who isn't logged in at all."""
    return {"ok": check_password(payload.password)}
