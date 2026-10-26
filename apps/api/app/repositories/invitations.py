from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Invitation, MembershipRole


def create_invitation(
    db: Session,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    role: MembershipRole,
    token_hash: str,
    expires_at: datetime,
    created_by: uuid.UUID,
    team_id: uuid.UUID | None = None,
) -> Invitation:
    row = Invitation(
        user_id=user_id,
        organization_id=organization_id,
        role=role,
        team_id=team_id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_by=created_by,
    )
    db.add(row)
    db.flush()
    return row


def get_invitation_by_token_hash(db: Session, token_hash: str) -> Invitation | None:
    return db.scalar(select(Invitation).where(Invitation.token_hash == token_hash))


def expire_pending_invitations(
    db: Session,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> None:
    """Invalidate outstanding invites so a reissue can mint a fresh token."""
    now = datetime.now(UTC)
    db.execute(
        update(Invitation)
        .where(
            Invitation.user_id == user_id,
            Invitation.organization_id == organization_id,
            Invitation.accepted_at.is_(None),
        )
        .values(expires_at=now)
    )
