import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Session, session)

    async def get_active_by_hash(self, refresh_token_hash: str) -> Session | None:
        now = datetime.now(UTC)
        stmt = select(Session).where(
            Session.refresh_token_hash == refresh_token_hash,
            Session.revoked_at.is_(None),
            Session.expires_at > now,
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def revoke_session(self, session_id: uuid.UUID) -> None:
        now = datetime.now(UTC)
        stmt = update(Session).where(Session.id == session_id).values(revoked_at=now)
        await self.session.execute(stmt)
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        now = datetime.now(UTC)
        stmt = (
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self.session.execute(stmt)
        await self.session.flush()
