from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.principal import Principal
from app.models import MembershipRole, Team
from app.repositories import teams as teams_repo
from app.repositories import users as users_repo


def create_team(db: Session, *, principal: Principal, name: str) -> Team:
    org_id = principal.active_coach_organization_id
    if org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        team = teams_repo.create_team(
            db,
            organization_id=org_id,
            name=name,
            created_by=principal.user_id,
        )
        teams_repo.add_team_member(db, team_id=team.id, user_id=principal.user_id)
        db.commit()
        db.refresh(team)
        return team
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Team name already exists in this club",
        ) from exc


def list_teams_for_principal(db: Session, *, principal: Principal) -> list[Team]:
    coach_org = principal.active_coach_organization_id
    if coach_org is not None:
        return teams_repo.list_teams_for_user(db, principal.user_id)

    admin_org = principal.active_club_admin_organization_id
    if admin_org is not None:
        return teams_repo.list_teams_for_organization(db, admin_org)

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def get_team_roster(
    db: Session,
    *,
    team_id: uuid.UUID,
) -> tuple[Team, list[dict]]:
    team = teams_repo.get_team_by_id(db, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    roster = []
    for _member, user in teams_repo.list_roster(db, team_id):
        memberships = users_repo.list_active_memberships(db, user.id)
        role = next(
            (m.role.value for m in memberships if m.organization_id == team.organization_id),
            None,
        )
        # Include invited players on the roster (membership may still be invited).
        if role is None:
            all_m = users_repo.list_memberships_for_user(db, user.id)
            role = next(
                (
                    m.role.value
                    for m in all_m
                    if m.organization_id == team.organization_id
                    and m.role == MembershipRole.PLAYER
                ),
                None,
            )
        roster.append(
            {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "role": role,
                "phone_e164": user.phone_e164,
            }
        )
    return team, roster
