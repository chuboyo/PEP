from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_principal
from app.core.principal import Principal
from app.db.session import get_db
from app.repositories import organizations as orgs_repo
from app.schemas.organizations import OrganizationOut

router = APIRouter(tags=["organizations"])


@router.get("/organizations/{organization_id}", response_model=OrganizationOut)
def get_organization(
    organization_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> OrganizationOut:
    organization = orgs_repo.get_organization_for_principal(db, principal, organization_id)
    return OrganizationOut(
        id=organization.id,
        name=organization.name,
        sport=organization.sport,
        country=organization.country,
        location=organization.location,
        logo_url=organization.logo_url,
        contact_email=organization.contact_email,
        status=organization.status,
    )
