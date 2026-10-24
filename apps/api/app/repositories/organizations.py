from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.principal import Principal
from app.models import Organization


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
