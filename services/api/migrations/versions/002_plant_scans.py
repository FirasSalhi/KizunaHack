"""002_plant_scans

Scan history of the plant Scanner (app/plants).

Revision ID: 002_plant_scans
Revises: 001_initial_auth
Create Date: 2026-11-22 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_plant_scans"
down_revision: str | None = "001_initial_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plant_scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("common_name", sa.String(length=200), nullable=False),
        sa.Column("scientific_name", sa.String(length=200), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sure", sa.Boolean(), nullable=False),
        sa.Column("engine", sa.String(length=100), nullable=False),
        sa.Column("health_status", sa.String(length=40), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_plant_scans_user_id", "plant_scans", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_plant_scans_user_id", table_name="plant_scans")
    op.drop_table("plant_scans")
