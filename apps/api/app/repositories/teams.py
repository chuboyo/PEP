from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Team, TeamMember, User


def create_team(
    db: Session,
    *,
    organization_id: uuid.UUID,
    name: str,
    created_by: uuid.UUID,
) -> Team:
    team = Team(
        organization_id=organization_id,
        name=name,
        created_by=created_by,
    )
    db.add(team)
    db.flush()
    return team


def add_team_member(
    db: Session,
    *,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TeamMember:
    existing = db.get(TeamMember, {"team_id": team_id, "user_id": user_id})
    if existing is not None:
        return existing
    row = TeamMember(team_id=team_id, user_id=user_id)
    db.add(row)
    db.flush()
    return row


def get_team_by_id(db: Session, team_id: uuid.UUID) -> Team | None:
    return db.get(Team, team_id)


def list_team_ids_for_user(db: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(select(TeamMember.team_id).where(TeamMember.user_id == user_id)).all()
    )


def list_teams_for_user(db: Session, user_id: uuid.UUID) -> list[Team]:
    return list(
        db.scalars(
            select(Team)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.user_id == user_id)
            .order_by(Team.name)
        ).all()
    )


def list_teams_for_organization(db: Session, organization_id: uuid.UUID) -> list[Team]:
    return list(
        db.scalars(
            select(Team)
            .where(Team.organization_id == organization_id)
            .order_by(Team.name)
        ).all()
    )


def list_roster(db: Session, team_id: uuid.UUID) -> list[tuple[TeamMember, User]]:
    rows = db.execute(
        select(TeamMember, User)
        .join(User, User.id == TeamMember.user_id)
        .where(TeamMember.team_id == team_id)
        .order_by(User.name)
    ).all()
    return [(tm, user) for tm, user in rows]
