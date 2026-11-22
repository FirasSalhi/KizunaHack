import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.farm import Farm
from app.models.membership import Membership
from app.repositories.base import BaseRepository


class FarmRepository(BaseRepository[Farm]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Farm, session)

    async def create_farm_with_owner(
        self,
        name: str,
        user_id: uuid.UUID,
        region: str = "Tunis",
    ) -> Farm:
        farm = Farm(name=name, region=region)
        self.session.add(farm)
        await self.session.flush()

        membership = Membership(
            farm_id=farm.id,
            user_id=user_id,
            role="owner",
        )
        self.session.add(membership)
        await self.session.flush()
        return farm

    async def get_user_memberships(self, user_id: uuid.UUID) -> List[Membership]:
        stmt = (
            select(Membership)
            .options(selectinload(Membership.farm))
            .where(Membership.user_id == user_id)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
