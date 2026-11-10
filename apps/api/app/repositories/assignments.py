from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, func, select
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
    Team,
    TeamMember,
    User,
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
    starts_on: date | None = None,
    ends_on: date | None = None,
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
        starts_on=starts_on,
        ends_on=ends_on,
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
    db: Session,
    *,
    coach_user_id: uuid.UUID,
    player_user_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> bool:
    coach_teams = (
        select(TeamMember.team_id)
        .join(Team, Team.id == TeamMember.team_id)
        .where(
            TeamMember.user_id == coach_user_id,
            Team.organization_id == organization_id,
        )
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
                    [
                        OccurrenceStatus.PENDING,
                        OccurrenceStatus.IN_PROGRESS,
                        OccurrenceStatus.COMPLETED,
                    ]
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
                [
                    OccurrenceStatus.PENDING,
                    OccurrenceStatus.IN_PROGRESS,
                    OccurrenceStatus.COMPLETED,
                ]
            )
        )
        .order_by(PlayerOccurrence.created_at.desc())
    ).all()
    return [(occurrence, assignment, name) for occurrence, assignment, name in rows]


def get_latest_open_occurrence_for_player(
    db: Session,
    player_id: uuid.UUID,
    *,
    channel: AssignmentChannel | None = None,
) -> PlayerOccurrence | None:
    stmt = select(PlayerOccurrence).where(
        PlayerOccurrence.player_id == player_id,
        PlayerOccurrence.status.in_(
            [OccurrenceStatus.PENDING, OccurrenceStatus.IN_PROGRESS]
        ),
    )
    if channel is not None:
        stmt = stmt.join(
            Assignment, Assignment.id == PlayerOccurrence.assignment_id
        ).where(Assignment.channel == channel)
    return db.scalar(
        stmt.order_by(PlayerOccurrence.created_at.desc()).limit(1)
    )


def get_latest_occurrence_for_player(
    db: Session,
    player_id: uuid.UUID,
    *,
    channel: AssignmentChannel | None = None,
) -> PlayerOccurrence | None:
    stmt = select(PlayerOccurrence).where(PlayerOccurrence.player_id == player_id)
    if channel is not None:
        stmt = stmt.join(
            Assignment, Assignment.id == PlayerOccurrence.assignment_id
        ).where(Assignment.channel == channel)
    return db.scalar(
        stmt.order_by(PlayerOccurrence.created_at.desc()).limit(1)
    )


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


def get_latest_team_assignment(
    db: Session,
    *,
    team_id: uuid.UUID,
    questionnaire_id: uuid.UUID | None = None,
) -> Assignment | None:
    stmt = select(Assignment).where(Assignment.team_id == team_id)
    if questionnaire_id is not None:
        stmt = stmt.where(Assignment.questionnaire_id == questionnaire_id)
    return db.scalar(stmt.order_by(Assignment.created_at.desc()).limit(1))


def get_questionnaire_name(db: Session, questionnaire_id: uuid.UUID) -> str | None:
    return db.scalar(
        select(Questionnaire.name).where(Questionnaire.id == questionnaire_id)
    )


def list_assignment_player_rows(
    db: Session, *, assignment_id: uuid.UUID
) -> list[tuple[PlayerOccurrence, User, Response | None]]:
    """Latest occurrence per player for this assignment (current window only).

    Recurring schedules keep many windows under one assignment; the dashboard
    must not list or aggregate every historical occurrence.
    """
    rows = db.execute(
        select(PlayerOccurrence, User, Response)
        .join(User, User.id == PlayerOccurrence.player_id)
        .outerjoin(Response, Response.occurrence_id == PlayerOccurrence.id)
        .where(PlayerOccurrence.assignment_id == assignment_id)
        .order_by(
            PlayerOccurrence.player_id.asc(),
            PlayerOccurrence.due_at.desc().nullslast(),
            PlayerOccurrence.created_at.desc(),
        )
    ).all()
    latest_by_player: dict[uuid.UUID, tuple[PlayerOccurrence, User, Response | None]] = {}
    for occurrence, user, response in rows:
        if occurrence.player_id not in latest_by_player:
            latest_by_player[occurrence.player_id] = (occurrence, user, response)
    result = list(latest_by_player.values())
    result.sort(key=lambda row: row[1].name.lower())
    return result


def list_roster_player_names(
    db: Session, *, team_id: uuid.UUID, organization_id: uuid.UUID
) -> dict[uuid.UUID, str]:
    rows = db.execute(
        select(User.id, User.name)
        .join(TeamMember, TeamMember.user_id == User.id)
        .join(
            Membership,
            (Membership.user_id == User.id)
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
    return {user_id: name for user_id, name in rows}


def list_questionnaire_history_for_players(
    db: Session,
    *,
    questionnaire_id: uuid.UUID,
    player_ids: list[uuid.UUID],
) -> list[tuple[PlayerOccurrence, Response | None]]:
    if not player_ids:
        return []
    rows = db.execute(
        select(PlayerOccurrence, Response)
        .join(Assignment, Assignment.id == PlayerOccurrence.assignment_id)
        .outerjoin(Response, Response.occurrence_id == PlayerOccurrence.id)
        .where(
            Assignment.questionnaire_id == questionnaire_id,
            PlayerOccurrence.player_id.in_(player_ids),
        )
        .order_by(
            PlayerOccurrence.player_id.asc(),
            PlayerOccurrence.due_at.desc().nullslast(),
            PlayerOccurrence.created_at.desc(),
        )
    ).all()
    return [(occurrence, response) for occurrence, response in rows]


def list_player_occurrence_history(
    db: Session,
    *,
    player_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> list[tuple[PlayerOccurrence, Assignment, str | None, Response | None]]:
    rows = db.execute(
        select(PlayerOccurrence, Assignment, Questionnaire.name, Response)
        .join(Assignment, Assignment.id == PlayerOccurrence.assignment_id)
        .outerjoin(
            Questionnaire, Questionnaire.id == Assignment.questionnaire_id
        )
        .outerjoin(Response, Response.occurrence_id == PlayerOccurrence.id)
        .where(
            PlayerOccurrence.player_id == player_id,
            PlayerOccurrence.organization_id == organization_id,
        )
        .order_by(
            Response.submitted_at.desc().nullslast(),
            PlayerOccurrence.created_at.desc(),
        )
    ).all()
    return [
        (occurrence, assignment, name, response)
        for occurrence, assignment, name, response in rows
    ]


def list_player_submissions(
    db: Session, *, player_id: uuid.UUID
) -> list[tuple[PlayerOccurrence, Assignment, str | None, Response]]:
    """Completed responses for a player, newest submitted_at first."""
    rows = db.execute(
        select(PlayerOccurrence, Assignment, Questionnaire.name, Response)
        .join(Assignment, Assignment.id == PlayerOccurrence.assignment_id)
        .join(Response, Response.occurrence_id == PlayerOccurrence.id)
        .outerjoin(
            Questionnaire, Questionnaire.id == Assignment.questionnaire_id
        )
        .where(PlayerOccurrence.player_id == player_id)
        .order_by(Response.submitted_at.desc())
    ).all()
    return [
        (occurrence, assignment, name, response)
        for occurrence, assignment, name, response in rows
    ]


def list_assignment_target_ids(
    db: Session, *, assignment_id: uuid.UUID
) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(AssignmentTarget.user_id).where(
                AssignmentTarget.assignment_id == assignment_id
            )
        ).all()
    )


def remove_assignment_targets_for_player_in_org(
    db: Session, *, player_id: uuid.UUID, organization_id: uuid.UUID
) -> None:
    db.execute(
        delete(AssignmentTarget).where(
            AssignmentTarget.user_id == player_id,
            AssignmentTarget.assignment_id.in_(
                select(Assignment.id).where(
                    Assignment.organization_id == organization_id
                )
            ),
        )
    )


def miss_open_occurrences_for_player_in_org(
    db: Session, *, player_id: uuid.UUID, organization_id: uuid.UUID
) -> int:
    rows = list(
        db.scalars(
            select(PlayerOccurrence).where(
                PlayerOccurrence.player_id == player_id,
                PlayerOccurrence.organization_id == organization_id,
                PlayerOccurrence.status.in_(
                    [OccurrenceStatus.PENDING, OccurrenceStatus.IN_PROGRESS]
                ),
            )
        ).all()
    )
    for occurrence in rows:
        occurrence.status = OccurrenceStatus.MISSED
    return len(rows)


def list_occurrences_due_in_window(
    db: Session, *, window_start: datetime, window_end: datetime
) -> list[tuple[PlayerOccurrence, Assignment]]:
    """pending/in_progress occurrences with due_at in [window_start, window_end]."""
    rows = db.execute(
        select(PlayerOccurrence, Assignment)
        .join(Assignment, Assignment.id == PlayerOccurrence.assignment_id)
        .where(
            PlayerOccurrence.status.in_(
                [OccurrenceStatus.PENDING, OccurrenceStatus.IN_PROGRESS]
            ),
            PlayerOccurrence.due_at.is_not(None),
            PlayerOccurrence.due_at >= window_start,
            PlayerOccurrence.due_at <= window_end,
        )
    ).all()
    return [(occurrence, assignment) for occurrence, assignment in rows]


def list_pending_past_due(
    db: Session, *, older_than: datetime
) -> list[PlayerOccurrence]:
    return list(
        db.scalars(
            select(PlayerOccurrence).where(
                PlayerOccurrence.status == OccurrenceStatus.PENDING,
                PlayerOccurrence.due_at.is_not(None),
                PlayerOccurrence.due_at < older_than,
            )
        ).all()
    )


def list_recurring_assignments(db: Session) -> list[Assignment]:
    return list(
        db.scalars(
            select(Assignment).where(
                Assignment.schedule.in_(
                    [AssignmentSchedule.DAILY, AssignmentSchedule.WEEKLY]
                )
            )
        ).all()
    )


def get_latest_occurrence_for_assignment_player(
    db: Session, *, assignment_id: uuid.UUID, player_id: uuid.UUID
) -> PlayerOccurrence | None:
    return db.scalar(
        select(PlayerOccurrence)
        .where(
            PlayerOccurrence.assignment_id == assignment_id,
            PlayerOccurrence.player_id == player_id,
        )
        .order_by(PlayerOccurrence.due_at.desc().nullslast())
        .limit(1)
    )


def occurrence_exists_for_window(
    db: Session,
    *,
    assignment_id: uuid.UUID,
    player_id: uuid.UUID,
    window_start: datetime,
) -> bool:
    return (
        db.scalar(
            select(PlayerOccurrence.id)
            .where(
                PlayerOccurrence.assignment_id == assignment_id,
                PlayerOccurrence.player_id == player_id,
                PlayerOccurrence.window_start == window_start,
            )
            .limit(1)
        )
        is not None
    )
