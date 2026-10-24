"""identity tables

Revision ID: 20261021_0002
Revises: 20261019_0001
Create Date: 2026-10-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261021_0002"
down_revision: Union[str, None] = "20261019_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_status = postgresql.ENUM(
    "invited",
    "active",
    "deactivated",
    name="user_status",
    create_type=False,
)
platform_role = postgresql.ENUM(
    "SUPERADMIN",
    name="platform_role",
    create_type=False,
)
organization_status = postgresql.ENUM(
    "active",
    "inactive",
    name="organization_status",
    create_type=False,
)
membership_role = postgresql.ENUM(
    "CLUB_ADMIN",
    "COACH",
    "PLAYER",
    name="membership_role",
    create_type=False,
)
membership_status = postgresql.ENUM(
    "invited",
    "active",
    "deactivated",
    name="membership_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    bind = op.get_bind()
    user_status.create(bind, checkfirst=True)
    platform_role.create(bind, checkfirst=True)
    organization_status.create(bind, checkfirst=True)
    membership_role.create(bind, checkfirst=True)
    membership_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("phone_e164", sa.Text(), nullable=True),
        sa.Column("status", user_status, nullable=False),
        sa.Column("platform_role", platform_role, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone_e164"),
    )

    op.create_table(
        "organizations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sport", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column("status", organization_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "memberships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", membership_role, nullable=False),
        sa.Column("status", membership_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_org"),
    )
    op.create_index(
        "uq_memberships_one_active_club_per_user",
        "memberships",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'deactivated'"),
    )
    op.create_index(
        "uq_memberships_one_active_club_admin",
        "memberships",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("role = 'CLUB_ADMIN' AND status <> 'deactivated'"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_index("uq_memberships_one_active_club_admin", table_name="memberships")
    op.drop_index("uq_memberships_one_active_club_per_user", table_name="memberships")
    op.drop_table("memberships")
    op.drop_table("organizations")
    op.drop_table("users")

    bind = op.get_bind()
    membership_status.drop(bind, checkfirst=True)
    membership_role.drop(bind, checkfirst=True)
    organization_status.drop(bind, checkfirst=True)
    platform_role.drop(bind, checkfirst=True)
    user_status.drop(bind, checkfirst=True)
