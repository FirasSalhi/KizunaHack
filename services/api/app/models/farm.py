import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimeStampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.membership import Membership


class Farm(Base, TimeStampMixin):
    __tablename__ = "farms"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    region: Mapped[str] = mapped_column(
        String(100),
        default="Tunis",
        nullable=False,
    )

    memberships: Mapped[list["Membership"]] = relationship(
        "Membership",
        back_populates="farm",
        cascade="all, delete-orphan",
    )
