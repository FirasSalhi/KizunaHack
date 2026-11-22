import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.memberships))
            .where(User.email == email.strip().lower())
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_with_memberships(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.memberships))
            .where(User.id == user_id)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()
