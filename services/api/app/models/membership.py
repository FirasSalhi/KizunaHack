import uuid
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimeStampMixin

if TYPE_CHECKING:
    from app.models.farm import Farm
    from app.models.user import User


class Membership(Base, TimeStampMixin):
    __tablename__ = "memberships"

    farm_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("farms.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),  # 'owner', 'operator', 'viewer'
        default="owner",
        nullable=False,
    )

    farm: Mapped["Farm"] = relationship("Farm", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="memberships")
