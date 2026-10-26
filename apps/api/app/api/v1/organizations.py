from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_current_principal,
    require_club_admin,
    require_superadmin,
)
from app.core.principal import Principal
from app.db.session import get_db
from app.repositories import organizations as orgs_repo
from app.schemas.organizations import (
    CoachInviteCreate,
    CoachInviteCreated,
    OrganizationCreate,
    OrganizationCreated,
    OrganizationListItem,
    OrganizationOut,
)
from app.services import invitations as invitations_service

router = APIRouter(tags=["organizations"])


@router.post("/organizations", response_model=OrganizationCreated)
def create_organization(
    body: OrganizationCreate,
    principal: Principal = Depends(require_superadmin),
    db: Session = Depends(get_db),
) -> OrganizationCreated:
    result = invitations_service.create_club_with_admin(
        db,
        principal=principal,
        name=body.name,
        admin_name=body.admin_name,
        admin_email=body.admin_email,
        sport=body.sport,
        country=body.country,
        location=body.location,
        logo_url=body.logo_url,
        contact_email=body.contact_email,
    )
    organization = orgs_repo.get_organization_by_id(db, result.organization_id)
    assert organization is not None
    return OrganizationCreated(
        id=organization.id,
        name=organization.name,
        status=organization.status.value,
        admin_email=result.invitee_email,
        invite_link=result.invite_link,
    )


@router.get("/organizations", response_model=list[OrganizationListItem])
def list_organizations(
    _: Principal = Depends(require_superadmin),
    db: Session = Depends(get_db),
) -> list[OrganizationListItem]:
    rows = orgs_repo.list_organizations_with_admin_email(db)
    return [
        OrganizationListItem(
            id=org.id,
            name=org.name,
            status=org.status.value,
            admin_email=admin_email,
        )
        for org, admin_email in rows
    ]


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
        status=organization.status.value,
    )


@router.post(
    "/organizations/{organization_id}/coaches",
    response_model=CoachInviteCreated,
)
def invite_coach(
    organization_id: uuid.UUID,
    body: CoachInviteCreate,
    principal: Principal = Depends(require_club_admin),
    db: Session = Depends(get_db),
) -> CoachInviteCreated:
    result = invitations_service.invite_coach(
        db,
        principal=principal,
        organization_id=organization_id,
        name=body.name,
        email=body.email,
    )
    return CoachInviteCreated(
        organization_id=result.organization_id,
        email=result.invitee_email,
        invite_link=result.invite_link,
    )
