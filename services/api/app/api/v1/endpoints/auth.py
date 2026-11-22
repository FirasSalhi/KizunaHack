from fastapi import APIRouter, Cookie, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


def _set_auth_cookies(response: Response, tokens: TokenResponse) -> None:
    """Set secure HTTP-only cookies according to FARMLINK specification."""
    # Access token cookie
    response.set_cookie(
        key="fl_access",
        value=tokens.access_token,
        max_age=tokens.expires_in,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    # Refresh token cookie
    response.set_cookie(
        key="fl_refresh",
        value=tokens.refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/api/v1/auth",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="fl_access", path="/")
    response.delete_cookie(key="fl_refresh", path="/api/v1/auth")


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user and initialize farm",
)
@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def signup(
    payload: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    user_agent: str | None = Header(None),
) -> TokenResponse:
    service = AuthService(db)
    _, tokens = await service.register(payload, user_agent=user_agent)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with email and password",
)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    user_agent: str | None = Header(None),
) -> TokenResponse:
    service = AuthService(db)
    _, tokens = await service.login(payload, user_agent=user_agent)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and issue new access token",
)
async def refresh(
    response: Response,
    body: RefreshRequest | None = None,
    fl_refresh: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db_session),
    user_agent: str | None = Header(None),
) -> TokenResponse:
    token_str = (body.refresh_token if body and body.refresh_token else None) or fl_refresh
    if not token_str:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)  # type: ignore

    service = AuthService(db)
    tokens = await service.refresh_tokens(token_str, user_agent=user_agent)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Log out and invalidate current session",
)
async def logout(
    response: Response,
    body: RefreshRequest | None = None,
    fl_refresh: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    token_str = (body.refresh_token if body and body.refresh_token else None) or fl_refresh
    service = AuthService(db)
    await service.logout(token_str)
    _clear_auth_cookies(response)
    return {"ok": True}


@router.post(
    "/logout-all",
    status_code=status.HTTP_200_OK,
    summary="Revoke all active sessions of current user",
)
async def logout_all(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    service = AuthService(db)
    await service.logout_all(current_user.id)
    _clear_auth_cookies(response)
    return {"ok": True}
