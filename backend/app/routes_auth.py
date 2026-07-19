from fastapi import APIRouter, HTTPException, Response

from app.auth import COOKIE_NAME, check_password, create_session
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
