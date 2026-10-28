from __future__ import annotations

from enum import Enum as PyEnum

from sqlalchemy import Enum


def pg_enum(enum_cls: type[PyEnum], name: str) -> Enum:
    """Postgres native ENUM column type (types created in Alembic migrations)."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda members: [member.value for member in members],
        create_type=False,
    )
