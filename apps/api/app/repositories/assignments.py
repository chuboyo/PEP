from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Assignment,
    AssignmentChannel,
    AssignmentSchedule,
    AssignmentTarget,
    AssignmentTargetType,
    Membership,
    MembershipRole,
    MembershipStatus,
    OccurrenceStatus,
    PlayerOccurrence,
    Questionnaire,
    Response,
    TeamMember,
)


def create_assignment(
    db: Session,
    *,
    organization_id: uuid.UUID,
    questionnaire_id: uuid.UUID,
    questions_snapshot: list[dict[str, Any]],
    created_by: uuid.UUID,
    target_type: AssignmentTargetType,
    team_id: uuid.UUID | None,
    schedule: AssignmentSchedule,
    due_at: datetime | None,
    channel: AssignmentChannel,
) -> Assignment:
    row = Assignment(
        organization_id=organization_id,
        questionnaire_id=questionnaire_id,
        questions_snapshot=questions_snapshot,
        created_by=created_by,
        target_type=target_type,
        team_id=team_id,
        schedule=schedule,
        due_at=due_at,
        channel=channel,
    )
    db.add(row)
    db.flush()
    return row


def add_assignment_target(
    db: Session, *, assignment_id: uuid.UUID, user_id: uuid.UUID
) -> AssignmentTarget:
    row = AssignmentTarget(assignment_id=assignment_id, user_id=user_id)
    db.add(row)
    db.flush()
    return row


def create_occurrence(
    db: Session,
    *,
    assignment_id: uuid.UUID,
    organization_id: uuid.UUID,
    player_id: uuid.UUID,
    window_start: datetime,
    due_at: datetime | None,
) -> PlayerOccurrence:
    row = PlayerOccurrence(
        assignment_id=assignment_id,
        organization_id=organization_id,
        player_id=player_id,
        window_start=window_start,
        status=OccurrenceStatus.PENDING,
        due_at=due_at,
        draft_answers={},
    )
    db.add(row)
    db.flush()
    return row


def list_player_ids_on_team(
    db: Session, *, team_id: uuid.UUID, organization_id: uuid.UUID
) -> list[uuid.UUID]:
    rows = db.scalars(
        select(TeamMember.user_id)
        .join(
            Membership,
            (Membership.user_id == TeamMember.user_id)
            & (Membership.organization_id == organization_id),
        )
        .where(
            TeamMember.team_id == team_id,
            Membership.role == MembershipRole.PLAYER,
            Membership.status.in_(
                [MembershipStatus.INVITED, MembershipStatus.ACTIVE]
            ),
        )
    ).all()
    return list(rows)


def player_shares_team_with_coach(
    db: Session, *, coach_user_id: uuid.UUID, player_user_id: uuid.UUID
) -> bool:
    coach_teams = select(TeamMember.team_id).where(
        TeamMember.user_id == coach_user_id
    )
    return (
        db.scalar(
            select(TeamMember.user_id).where(
                TeamMember.user_id == player_user_id,
                TeamMember.team_id.in_(coach_teams),
            ).limit(1)
        )
        is not None
    )


def get_occurrence_by_id(
    db: Session, occurrence_id: uuid.UUID
) -> PlayerOccurrence | None:
    return db.get(PlayerOccurrence, occurrence_id)


def list_occurrences_for_player(
    db: Session, player_id: uuid.UUID
) -> list[PlayerOccurrence]:
    return list(
        db.scalars(
            select(PlayerOccurrence)
            .where(PlayerOccurrence.player_id == player_id)
            .where(
                PlayerOccurrence.status.in_(
                    [OccurrenceStatus.PENDING, OccurrenceStatus.COMPLETED]
                )
            )
            .order_by(PlayerOccurrence.created_at.desc())
        ).all()
    )


def list_occurrence_details_for_player(
    db: Session, player_id: uuid.UUID
) -> list[tuple[PlayerOccurrence, Assignment, str | None]]:
    rows = db.execute(
        select(PlayerOccurrence, Assignment, Questionnaire.name)
        .join(Assignment, Assignment.id == PlayerOccurrence.assignment_id)
        .outerjoin(
            Questionnaire, Questionnaire.id == Assignment.questionnaire_id
        )
        .where(PlayerOccurrence.player_id == player_id)
        .where(
            PlayerOccurrence.status.in_(
                [OccurrenceStatus.PENDING, OccurrenceStatus.COMPLETED]
            )
        )
        .order_by(PlayerOccurrence.created_at.desc())
    ).all()
    return [(occurrence, assignment, name) for occurrence, assignment, name in rows]


def get_assignment_by_id(db: Session, assignment_id: uuid.UUID) -> Assignment | None:
    return db.get(Assignment, assignment_id)


def get_response_for_occurrence(
    db: Session, occurrence_id: uuid.UUID
) -> Response | None:
    return db.scalar(
        select(Response).where(Response.occurrence_id == occurrence_id)
    )


def create_response(
    db: Session,
    *,
    occurrence_id: uuid.UUID,
    organization_id: uuid.UUID,
    player_id: uuid.UUID,
    channel: AssignmentChannel,
    answers: dict[str, Any],
    questions_snapshot: list[dict[str, Any]],
) -> Response:
    row = Response(
        occurrence_id=occurrence_id,
        organization_id=organization_id,
        player_id=player_id,
        channel=channel,
        answers=answers,
        questions_snapshot=questions_snapshot,
    )
    db.add(row)
    db.flush()
    return row


def count_occurrences_for_assignment(db: Session, assignment_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(PlayerOccurrence)
            .where(PlayerOccurrence.assignment_id == assignment_id)
        )
        or 0
    )
