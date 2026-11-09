"""deliveries table for WhatsApp outbound messages

Revision ID: 20261102_0009
Revises: 20261029_0008
Create Date: 2026-11-02 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261102_0009"
down_revision: Union[str, None] = "20261029_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

delivery_kind = postgresql.ENUM(
    "survey_start",
    "question",
    "reminder",
    name="delivery_kind",
    create_type=False,
)

delivery_status = postgresql.ENUM(
    "queued",
    "sent",
    "delivered",
    "read",
    "responded",
    "failed",
    name="delivery_status",
    create_type=False,
)


def upgrade() -> None:
    delivery_kind.create(op.get_bind(), checkfirst=True)
    delivery_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "deliveries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("occurrence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("kind", delivery_kind, nullable=False),
        sa.Column("status", delivery_status, nullable=False),
        sa.Column("provider_message_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["occurrence_id"], ["player_occurrences.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_deliveries_provider_message_id",
        "deliveries",
        ["provider_message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_deliveries_provider_message_id", table_name="deliveries")
    op.drop_table("deliveries")
    delivery_status.drop(op.get_bind(), checkfirst=True)
    delivery_kind.drop(op.get_bind(), checkfirst=True)
