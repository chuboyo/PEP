from __future__ import annotations

import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.principal import MembershipInfo, Principal
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import MembershipRole, UserStatus
from app.repositories import organizations as orgs_repo
from app.repositories import teams as teams_repo
from app.repositories import users as users_repo

_bearer = HTTPBearer(auto_error=False)


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        user_id = decode_access_token(credentials.credentials)
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        ) from None

    user = users_repo.get_user_by_id(db, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    memberships = users_repo.list_active_memberships(db, user.id)
    team_ids = teams_repo.list_team_ids_for_user(db, user.id)
    return Principal(
        user_id=user.id,
        platform_role=user.platform_role.value if user.platform_role else None,
        memberships=[
            MembershipInfo(
                organization_id=m.organization_id,
                role=m.role.value,
                status=m.status.value,
            )
            for m in memberships
        ],
        team_ids=team_ids,
    )


def require_superadmin(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if not principal.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return principal


def require_club_admin(
    organization_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Principal:
    organization = orgs_repo.get_organization_by_id(db, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    role = principal.active_role_in(organization_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if role != MembershipRole.CLUB_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return principal


def require_coach(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if principal.active_coach_organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return principal


def require_coach_on_team(
    team_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Principal:
    team = teams_repo.get_team_by_id(db, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    coach_org = principal.active_coach_organization_id
    if coach_org is None or team.organization_id != coach_org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not principal.is_on_team(team_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return principal
