import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.session import Session
from app.models.user import User
from app.repositories.farm_repository import FarmRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    FarmMembershipResponse,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    TokenResponse,
)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.session_repo = SessionRepository(session)
        self.farm_repo = FarmRepository(session)

    async def register(
        self,
        payload: RegisterRequest,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, TokenResponse]:
        # 1. Check if user already exists
        existing = await self.user_repo.get_by_email(payload.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": {"code": "USER_EXISTS", "message": "A user with this email already exists."}},
            )

        # 2. Create user with hashed password
        hashed_pw = hash_password(payload.password)
        user = User(
            email=payload.email.strip().lower(),
            name=payload.name.strip(),
            password_hash=hashed_pw,
            locale=payload.locale,
        )
        await self.user_repo.create(user)

        # 3. Create default farm for user (FarmLink tenancy model)
        farm_name = payload.farm_name.strip() if payload.farm_name else f"{user.name}'s Farm"
        await self.farm_repo.create_farm_with_owner(
            name=farm_name,
            user_id=user.id,
        )

        # 4. Generate tokens and session
        tokens = await self._create_tokens_and_session(user.id, user_agent)
        return user, tokens

    async def login(
        self,
        payload: LoginRequest,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, TokenResponse]:
        user = await self.user_repo.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}},
            )

        if user.disabled_at is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "USER_DISABLED", "message": "This account has been deactivated."}},
            )

        tokens = await self._create_tokens_and_session(user.id, user_agent)
        return user, tokens

    async def refresh_tokens(
        self,
        refresh_token: str,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        token_hash = hash_refresh_token(refresh_token)
        session = await self.session_repo.get_active_by_hash(token_hash)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is expired or revoked."}},
            )

        # Revoke old session (token rotation)
        await self.session_repo.revoke_session(session.id)

        # Create new tokens and session
        return await self._create_tokens_and_session(session.user_id, user_agent)

    async def logout(self, refresh_token: Optional[str] = None) -> None:
        if refresh_token:
            token_hash = hash_refresh_token(refresh_token)
            session = await self.session_repo.get_active_by_hash(token_hash)
            if session:
                await self.session_repo.revoke_session(session.id)

    async def logout_all(self, user_id: uuid.UUID) -> None:
        await self.session_repo.revoke_all_for_user(user_id)

    async def get_me(self, user_id: uuid.UUID) -> MeResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found."}},
            )

        memberships = await self.farm_repo.get_user_memberships(user_id)
        membership_responses = [
            FarmMembershipResponse(
                farm_id=m.farm_id,
                farm_name=m.farm.name if m.farm else "Farm",
                role=m.role,
            )
            for m in memberships
        ]

        return MeResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            locale=user.locale,
            memberships=membership_responses,
        )

    async def _create_tokens_and_session(
        self,
        user_id: uuid.UUID,
        user_agent: Optional[str],
    ) -> TokenResponse:
        access_token = create_access_token(
            subject=str(user_id),
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        raw_refresh, refresh_hash = create_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_session = Session(
            user_id=user_id,
            refresh_token_hash=refresh_hash,
            expires_at=expires_at,
            user_agent=user_agent[:300] if user_agent else None,
        )
        await self.session_repo.create(new_session)

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
