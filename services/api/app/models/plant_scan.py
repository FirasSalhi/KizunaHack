import uuid
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimeStampMixin, generate_uuid


class PlantScan(Base, TimeStampMixin):
    """One plant photo scanned with the Scanner (app/plants), with its full result."""

    __tablename__ = "plant_scans"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    common_name: Mapped[str] = mapped_column(String(200), nullable=False)
    scientific_name: Mapped[str] = mapped_column(String(200), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    sure: Mapped[bool] = mapped_column(Boolean, nullable=False)
    engine: Mapped[str] = mapped_column(String(100), nullable=False)
    health_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
