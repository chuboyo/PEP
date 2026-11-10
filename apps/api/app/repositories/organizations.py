from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.principal import Principal
from app.models import (
    Membership,
    MembershipRole,
    MembershipStatus,
    OccurrenceStatus,
    Organization,
    OrganizationStatus,
    PlayerOccurrence,
    User,
)


def get_organization_by_id(db: Session, organization_id: uuid.UUID) -> Organization | None:
    return db.get(Organization, organization_id)


def get_organization_for_principal(
    db: Session,
    principal: Principal,
    organization_id: uuid.UUID,
) -> Organization:
    """Return the organization if the principal may see it; otherwise 404."""
    organization = get_organization_by_id(db, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if principal.is_superadmin:
        return organization

    if principal.has_active_membership(organization_id):
        return organization

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def create_organization(
    db: Session,
    *,
    name: str,
    sport: str | None = None,
    country: str | None = None,
    location: str | None = None,
    logo_url: str | None = None,
    contact_email: str | None = None,
    status: OrganizationStatus = OrganizationStatus.ACTIVE,
) -> Organization:
    organization = Organization(
        name=name,
        sport=sport,
        country=country,
        location=location,
        logo_url=logo_url,
        contact_email=contact_email,
        status=status,
    )
    db.add(organization)
    db.flush()
    return organization


def list_organizations(db: Session) -> list[Organization]:
    return list(db.scalars(select(Organization).order_by(Organization.name)).all())


def list_organizations_with_admin_email(
    db: Session,
) -> list[tuple[Organization, str | None]]:
    orgs = list_organizations(db)
    rows: list[tuple[Organization, str | None]] = []
    for org in orgs:
        admin_email = db.scalar(
            select(User.email)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.organization_id == org.id,
                Membership.role == MembershipRole.CLUB_ADMIN,
                Membership.status != MembershipStatus.DEACTIVATED,
            )
            .limit(1)
        )
        rows.append((org, admin_email))
    return rows


def count_memberships(
    db: Session,
    *,
    organization_id: uuid.UUID,
    role: MembershipRole,
    statuses: list[MembershipStatus],
) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.organization_id == organization_id,
                Membership.role == role,
                Membership.status.in_(statuses),
            )
        )
        or 0
    )


def list_player_ids_in_organization(
    db: Session,
    *,
    organization_id: uuid.UUID,
    statuses: list[MembershipStatus],
) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(Membership.user_id).where(
                Membership.organization_id == organization_id,
                Membership.role == MembershipRole.PLAYER,
                Membership.status.in_(statuses),
            )
        ).all()
    )


def count_occurrences(
    db: Session,
    *,
    organization_id: uuid.UUID,
    status: OccurrenceStatus | None = None,
) -> int:
    stmt = (
        select(func.count())
        .select_from(PlayerOccurrence)
        .where(PlayerOccurrence.organization_id == organization_id)
    )
    if status is not None:
        stmt = stmt.where(PlayerOccurrence.status == status)
    return int(db.scalar(stmt) or 0)


def get_membership_for_org_role(
    db: Session,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    role: MembershipRole,
) -> Membership | None:
    return db.scalar(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
            Membership.role == role,
        )
    )


def list_coaches_for_organization(
    db: Session, *, organization_id: uuid.UUID
) -> list[tuple[User, Membership]]:
    rows = db.execute(
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.organization_id == organization_id,
            Membership.role == MembershipRole.COACH,
            Membership.status != MembershipStatus.DEACTIVATED,
        )
        .order_by(User.name.asc())
    ).all()
    return [(user, membership) for user, membership in rows]


def list_active_coach_ids(
    db: Session, *, organization_id: uuid.UUID, exclude_user_id: uuid.UUID | None = None
) -> list[uuid.UUID]:
    stmt = select(Membership.user_id).where(
        Membership.organization_id == organization_id,
        Membership.role == MembershipRole.COACH,
        Membership.status == MembershipStatus.ACTIVE,
    )
    if exclude_user_id is not None:
        stmt = stmt.where(Membership.user_id != exclude_user_id)
    return list(db.scalars(stmt).all())
