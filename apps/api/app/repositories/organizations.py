from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.principal import Principal
from app.models import Membership, MembershipRole, MembershipStatus, Organization, OrganizationStatus, User


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
