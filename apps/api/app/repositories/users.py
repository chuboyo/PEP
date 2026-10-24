from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Membership, MembershipStatus, PlatformRole, RefreshToken, User, UserStatus


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_superadmin(db: Session) -> User | None:
    return db.scalar(
        select(User).where(User.platform_role == PlatformRole.SUPERADMIN).limit(1)
    )


def list_active_memberships(db: Session, user_id: uuid.UUID) -> list[Membership]:
    return list(
        db.scalars(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        ).all()
    )


def create_user(
    db: Session,
    *,
    email: str,
    name: str,
    password_hash: str | None,
    status: UserStatus,
    platform_role: PlatformRole | None = None,
) -> User:
    user = User(
        email=email,
        name=name,
        password_hash=password_hash,
        status=status,
        platform_role=platform_role,
    )
    db.add(user)
    db.flush()
    return user


def create_refresh_token(
    db: Session,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at,
) -> RefreshToken:
    row = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(row)
    db.flush()
    return row


def get_refresh_token_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
    return db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
