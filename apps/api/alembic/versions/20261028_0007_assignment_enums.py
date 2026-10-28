"""convert assignment text columns to postgres enums

Revision ID: 20261028_0007
Revises: 20261028_0006
Create Date: 2026-10-28 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261028_0007"
down_revision: Union[str, None] = "20261028_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

assignment_target_type = postgresql.ENUM(
    "team",
    "players",
    name="assignment_target_type",
    create_type=False,
)
assignment_schedule = postgresql.ENUM(
    "once",
    "daily",
    "weekly",
    name="assignment_schedule",
    create_type=False,
)
assignment_channel = postgresql.ENUM(
    "in_app",
    "whatsapp",
    name="assignment_channel",
    create_type=False,
)
occurrence_status = postgresql.ENUM(
    "pending",
    "in_progress",
    "completed",
    "missed",
    name="occurrence_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    assignment_target_type.create(bind, checkfirst=True)
    assignment_schedule.create(bind, checkfirst=True)
    assignment_channel.create(bind, checkfirst=True)
    occurrence_status.create(bind, checkfirst=True)

    op.execute(
        """
        ALTER TABLE assignments
        ALTER COLUMN target_type TYPE assignment_target_type
        USING target_type::assignment_target_type
        """
    )
    op.execute(
        """
        ALTER TABLE assignments
        ALTER COLUMN schedule TYPE assignment_schedule
        USING schedule::assignment_schedule
        """
    )
    op.execute(
        """
        ALTER TABLE assignments
        ALTER COLUMN channel TYPE assignment_channel
        USING channel::assignment_channel
        """
    )
    op.execute(
        """
        ALTER TABLE player_occurrences
        ALTER COLUMN status TYPE occurrence_status
        USING status::occurrence_status
        """
    )
    op.execute(
        """
        ALTER TABLE responses
        ALTER COLUMN channel TYPE assignment_channel
        USING channel::assignment_channel
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE responses
        ALTER COLUMN channel TYPE text
        USING channel::text
        """
    )
    op.execute(
        """
        ALTER TABLE player_occurrences
        ALTER COLUMN status TYPE text
        USING status::text
        """
    )
    op.execute(
        """
        ALTER TABLE assignments
        ALTER COLUMN channel TYPE text
        USING channel::text
        """
    )
    op.execute(
        """
        ALTER TABLE assignments
        ALTER COLUMN schedule TYPE text
        USING schedule::text
        """
    )
    op.execute(
        """
        ALTER TABLE assignments
        ALTER COLUMN target_type TYPE text
        USING target_type::text
        """
    )

    bind = op.get_bind()
    occurrence_status.drop(bind, checkfirst=True)
    assignment_channel.drop(bind, checkfirst=True)
    assignment_schedule.drop(bind, checkfirst=True)
    assignment_target_type.drop(bind, checkfirst=True)
