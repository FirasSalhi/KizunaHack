import uuid
from collections.abc import AsyncGenerator

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

# Support both Bearer header and fl_access cookie (as specified in rest-api.md)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


async def get_current_user(
    db: AsyncSession = Depends(get_db_session),
    auth_header: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    fl_access: str | None = Cookie(None),
) -> User:
    token: str | None = None
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    elif fl_access:
        token = fl_access

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "NOT_AUTHENTICATED", "message": "Authentication required."}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid or expired token."}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Malformed token subject."}},
        ) from err

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User no longer exists."}},
        )

    if user.disabled_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "USER_DISABLED", "message": "Account has been deactivated."}},
        )

    return user


async def get_optional_user(
    db: AsyncSession = Depends(get_db_session),
    auth_header: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    fl_access: str | None = Cookie(None),
) -> User | None:
    """The signed-in user, or None for visitors and the dashboard's demo session (no error)."""
    token = auth_header.credentials if auth_header and auth_header.credentials else fl_access
    payload = decode_access_token(token) if token else None
    if not payload or not payload.get("sub"):
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        return None
    user = await UserRepository(db).get_by_id(user_id)
    if user is None or user.disabled_at is not None:
        return None
    return user
