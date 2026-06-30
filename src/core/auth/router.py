"""Auth router: login, logout, me, password change."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from core.auth.deps import get_current_user
from core.auth.jwt import create_access_token
from core.auth.password import hash_password, validate_password_strength, verify_password
from core.users.models import User
from extensions.registry import registry
from extensions.protocols import AuthProvider
from shared.environment import is_production
from shared.limiter import limiter
from shared.webpage import webpage

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_NAME = "access_token"
_COOKIE_MAX_AGE = 60 * 60 * 24  # 24h


def _is_production() -> bool:
    """委派至共用 ``is_production()`` helper（單一事實來源）。

    保留薄包裝以相容既有測試對 ``_is_production()`` 的直接呼叫；
    正式環境判定同時接受 ``prod`` 與 ``production``。
    """
    return is_production()


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    display_name: str


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, response: Response):
    provider: AuthProvider = registry.get(AuthProvider, "local")
    try:
        user = await provider.authenticate(
            {"username": body.username, "password": body.password}
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(user_id=str(user.id), permissions=user.permissions)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        secure=_is_production(),
    )
    return {"message": "Logged in", "permissions": user.permissions}


@router.post("/logout")
@webpage.redirect(status_code=302)
async def logout(request: Request):
    redirect = RedirectResponse(url=str(request.url_for("login_page")), status_code=302)
    redirect.delete_cookie(key=_COOKIE_NAME)
    return redirect


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "display_name": current_user.display_name,
        "permissions": current_user.permissions,
        "tags": current_user.tags,
    }


@router.put("/profile")
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
):
    """Update only display_name. All other fields are ignored for self-edit."""
    current_user.display_name = body.display_name
    await current_user.save()
    return {"display_name": current_user.display_name}


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    response: Response = None,
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    try:
        validate_password_strength(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    current_user.hashed_password = hash_password(body.new_password)
    await current_user.save()

    # Invalidate existing session
    response.delete_cookie(key=_COOKIE_NAME)
    return {"message": "Password changed. Please log in again."}
