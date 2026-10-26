from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlencode

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.core.principal import Principal
from app.models import (
    Membership,
    MembershipRole,
    MembershipStatus,
    OrganizationStatus,
    User,
    UserStatus,
)
from app.repositories import invitations as invitations_repo
from app.repositories import organizations as orgs_repo
from app.repositories import users as users_repo
from app.schemas.auth import TokenResponse
from app.services import auth as auth_service
from app.services.invite_delivery import InviteDelivery, default_invite_delivery


@dataclass(frozen=True)
class InviteResult:
    organization_id: uuid.UUID
    invite_link: str
    invitee_email: str


def _build_invite_link(raw_token: str) -> str:
    settings = get_settings()
    base = settings.app_public_url.rstrip("/")
    return f"{base}/accept-invite?{urlencode({'token': raw_token})}"


def _pending_membership_for_reissue(
    db: Session,
    *,
    email: str,
    organization_id: uuid.UUID,
) -> tuple[User | None, Membership | None]:
    """Validate the email for invite/reissue.

    Returns (user, existing same-org membership to reuse) when the row is
    INVITED or DEACTIVATED. Raises 409 for credentialed users or conflicts.
    """
    user = users_repo.get_user_by_email(db, email)
    if user is None:
        return None, None

    # Never attach invites to platform accounts or users who already have credentials.
    if user.platform_role is not None or user.password_hash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is not available for invitation",
        )
    if user.status == UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is not available for invitation",
        )

    reusable_here: Membership | None = None
    for membership in users_repo.list_memberships_for_user(db, user.id):
        if membership.organization_id == organization_id:
            if membership.status == MembershipStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User already has a membership in this club",
                )
            # Reuse INVITED or DEACTIVATED row — unique (user_id, organization_id).
            if membership.status in (
                MembershipStatus.INVITED,
                MembershipStatus.DEACTIVATED,
            ):
                reusable_here = membership
            continue

        if membership.status == MembershipStatus.DEACTIVATED:
            continue
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already belongs to another club",
        )

    return user, reusable_here


def create_invitation_for_email(
    db: Session,
    *,
    organization_id: uuid.UUID,
    email: str,
    name: str,
    role: MembershipRole,
    created_by: uuid.UUID,
    delivery: InviteDelivery = default_invite_delivery,
) -> InviteResult:
    user, existing_membership = _pending_membership_for_reissue(
        db, email=email, organization_id=organization_id
    )

    if role == MembershipRole.CLUB_ADMIN:
        existing_admin = users_repo.get_club_admin_membership(db, organization_id)
        if existing_admin is not None and (
            existing_membership is None or existing_admin.id != existing_membership.id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Club already has a club admin",
            )

    if user is None:
        user = users_repo.create_user(
            db,
            email=email,
            name=name,
            password_hash=None,
            status=UserStatus.INVITED,
        )
    else:
        user.name = name
        user.status = UserStatus.INVITED

    if existing_membership is None:
        users_repo.create_membership(
            db,
            user_id=user.id,
            organization_id=organization_id,
            role=role,
            status=MembershipStatus.INVITED,
        )
    else:
        existing_membership.role = role
        existing_membership.status = MembershipStatus.INVITED
        invitations_repo.expire_pending_invitations(
            db, user_id=user.id, organization_id=organization_id
        )

    raw_token = security.generate_invite_token()
    token_hash = security.hash_invite_token(raw_token)
    invitations_repo.create_invitation(
        db,
        user_id=user.id,
        organization_id=organization_id,
        role=role,
        token_hash=token_hash,
        expires_at=security.invite_token_expiry(),
        created_by=created_by,
    )

    invite_link = _build_invite_link(raw_token)
    delivery.deliver(email=email, invite_link=invite_link)
    db.commit()
    return InviteResult(
        organization_id=organization_id,
        invite_link=invite_link,
        invitee_email=email,
    )


def create_club_with_admin(
    db: Session,
    *,
    principal: Principal,
    name: str,
    admin_name: str,
    admin_email: str,
    sport: str | None = None,
    country: str | None = None,
    location: str | None = None,
    logo_url: str | None = None,
    contact_email: str | None = None,
    delivery: InviteDelivery = default_invite_delivery,
) -> InviteResult:
    organization = orgs_repo.create_organization(
        db,
        name=name,
        sport=sport,
        country=country,
        location=location,
        logo_url=logo_url,
        contact_email=contact_email,
        status=OrganizationStatus.ACTIVE,
    )
    return create_invitation_for_email(
        db,
        organization_id=organization.id,
        email=admin_email,
        name=admin_name,
        role=MembershipRole.CLUB_ADMIN,
        created_by=principal.user_id,
        delivery=delivery,
    )


def invite_coach(
    db: Session,
    *,
    principal: Principal,
    organization_id: uuid.UUID,
    name: str,
    email: str,
    delivery: InviteDelivery = default_invite_delivery,
) -> InviteResult:
    return create_invitation_for_email(
        db,
        organization_id=organization_id,
        email=email,
        name=name,
        role=MembershipRole.COACH,
        created_by=principal.user_id,
        delivery=delivery,
    )


def accept_invite(db: Session, *, token: str, password: str) -> TokenResponse:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    token_hash = security.hash_invite_token(token)
    invitation = invitations_repo.get_invitation_by_token_hash(db, token_hash)
    now = datetime.now(UTC)

    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation",
        )

    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    if invitation.accepted_at is not None or expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation",
        )

    user = users_repo.get_user_by_id(db, invitation.user_id)
    # Accept only invitation-only accounts (no credentials / platform role yet).
    if (
        user is None
        or user.status != UserStatus.INVITED
        or user.password_hash is not None
        or user.platform_role is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation",
        )

    memberships = users_repo.list_memberships_for_user(db, user.id)
    membership = next(
        (
            m
            for m in memberships
            if m.organization_id == invitation.organization_id
            and m.status == MembershipStatus.INVITED
        ),
        None,
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation",
        )

    user.password_hash = security.hash_password(password)
    user.status = UserStatus.ACTIVE
    membership.status = MembershipStatus.ACTIVE
    invitation.accepted_at = now
    db.flush()
    return auth_service.issue_token_pair(db, user.id)
