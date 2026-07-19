from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import COOKIE_NAME, check_password, create_session, require_auth
from app.models import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    if not check_password(payload.password):
        raise HTTPException(status_code=401, detail="Wrong password")

    token = create_session()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=14 * 24 * 3600,
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.post("/verify", dependencies=[Depends(require_auth)])
def verify(payload: LoginRequest):
    """Re-check the password without touching the session -- used to
    gate revealing a masked secret in the UI. Requires an already-valid
    session too, so this can't be used as a bare password-guessing
    oracle by someone who isn't logged in at all."""
    return {"ok": check_password(payload.password)}
