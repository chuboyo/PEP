from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_current_principal,
    require_coach,
    require_coach_on_team,
)
from app.core.principal import Principal
from app.db.session import get_db
from app.schemas.dashboard import TeamDashboardOut
from app.schemas.teams import (
    PlayerInviteCreate,
    PlayerInviteCreated,
    TeamCreate,
    TeamDetailOut,
    TeamMemberOut,
    TeamOut,
)
from app.services import dashboard as dashboard_service
from app.services import invitations as invitations_service
from app.services import teams as teams_service

router = APIRouter(tags=["teams"])


@router.post("/teams", response_model=TeamOut)
def create_team(
    body: TeamCreate,
    principal: Principal = Depends(require_coach),
    db: Session = Depends(get_db),
) -> TeamOut:
    team = teams_service.create_team(db, principal=principal, name=body.name)
    return TeamOut(id=team.id, organization_id=team.organization_id, name=team.name)


@router.get("/teams", response_model=list[TeamOut])
def list_teams(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[TeamOut]:
    teams = teams_service.list_teams_for_principal(db, principal=principal)
    return [
        TeamOut(id=t.id, organization_id=t.organization_id, name=t.name) for t in teams
    ]


@router.get("/teams/{team_id}", response_model=TeamDetailOut)
def get_team(
    team_id: uuid.UUID,
    _: Principal = Depends(require_coach_on_team),
    db: Session = Depends(get_db),
) -> TeamDetailOut:
    team, roster = teams_service.get_team_roster(db, team_id=team_id)
    return TeamDetailOut(
        id=team.id,
        organization_id=team.organization_id,
        name=team.name,
        members=[TeamMemberOut(**m) for m in roster],
    )


@router.get("/teams/{team_id}/dashboard", response_model=TeamDashboardOut)
def get_team_dashboard(
    team_id: uuid.UUID,
    principal: Principal = Depends(require_coach_on_team),
    db: Session = Depends(get_db),
    questionnaire_id: uuid.UUID | None = Query(default=None),
) -> TeamDashboardOut:
    return dashboard_service.get_team_dashboard(
        db,
        principal=principal,
        team_id=team_id,
        questionnaire_id=questionnaire_id,
    )


@router.post("/teams/{team_id}/players", response_model=PlayerInviteCreated)
def invite_player(
    team_id: uuid.UUID,
    body: PlayerInviteCreate,
    principal: Principal = Depends(require_coach_on_team),
    db: Session = Depends(get_db),
) -> PlayerInviteCreated:
    result = invitations_service.invite_player(
        db,
        principal=principal,
        team_id=team_id,
        name=body.name,
        email=body.email,
        phone_e164=body.phone_e164,
    )
    assert result.team_id is not None
    return PlayerInviteCreated(
        organization_id=result.organization_id,
        team_id=result.team_id,
        email=result.invitee_email,
        invite_link=result.invite_link,
    )
