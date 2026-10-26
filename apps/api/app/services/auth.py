from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core import security
from app.models import UserStatus
from app.repositories import users as users_repo
from app.schemas.auth import TokenResponse


def issue_token_pair(db: Session, user_id) -> TokenResponse:
    access_token = security.create_access_token(user_id)
    refresh_token = security.generate_refresh_token()
    users_repo.create_refresh_token(
        db,
        user_id=user_id,
        token_hash=security.hash_refresh_token(refresh_token),
        expires_at=security.refresh_token_expiry(),
    )
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


def login(db: Session, email: str, password: str) -> TokenResponse:
    user = users_repo.get_user_by_email(db, email)
    if (
        user is None
        or user.password_hash is None
        or user.status != UserStatus.ACTIVE
        or not security.verify_password(user.password_hash, password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return issue_token_pair(db, user.id)


def refresh(db: Session, refresh_token: str) -> TokenResponse:
    token_hash = security.hash_refresh_token(refresh_token)
    row = users_repo.get_refresh_token_by_hash(db, token_hash)
    now = datetime.now(UTC)
    expires_at = row.expires_at if row is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if row is None or row.revoked_at is not None or expires_at is None or expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = users_repo.get_user_by_id(db, row.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    row.revoked_at = now
    db.flush()
    return issue_token_pair(db, user.id)


def logout(db: Session, refresh_token: str) -> None:
    token_hash = security.hash_refresh_token(refresh_token)
    row = users_repo.get_refresh_token_by_hash(db, token_hash)
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        db.commit()
