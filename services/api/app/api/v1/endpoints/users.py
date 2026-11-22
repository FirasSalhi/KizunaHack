from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.user import User
from app.schemas.auth import MeResponse
from app.schemas.user import UserResponse, UserUpdate
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter()


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current user profile and farm memberships",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MeResponse:
    service = AuthService(db)
    return await service.get_me(current_user.id)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile (name, locale)",
)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    service = UserService(db)
    return await service.update_user(current_user.id, payload)
