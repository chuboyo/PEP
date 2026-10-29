from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.principal import Principal
from app.models import (
    Assignment,
    AssignmentChannel,
    AssignmentSchedule,
    AssignmentTargetType,
    MembershipRole,
    MembershipStatus,
    OccurrenceStatus,
    Response,
)
from app.repositories import assignments as assignments_repo
from app.repositories import questionnaires as questionnaires_repo
from app.repositories import teams as teams_repo
from app.repositories import users as users_repo
from app.schemas.answers import validate_answers
from app.schemas.player_history import (
    PlayerHistoryItemOut,
    PlayerHistoryOut,
    RatingTrendOut,
)


def _require_coach_org(principal: Principal) -> uuid.UUID:
    org_id = principal.active_coach_organization_id
    if org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return org_id


def create_assignment(
    db: Session,
    *,
    principal: Principal,
    questionnaire_id: uuid.UUID,
    target_type: AssignmentTargetType,
    team_id: uuid.UUID | None,
    player_ids: list[uuid.UUID] | None,
    due_at: datetime | None,
    channel: AssignmentChannel,
    schedule: AssignmentSchedule,
) -> tuple[Assignment, int]:
    org_id = _require_coach_org(principal)

    if channel != AssignmentChannel.IN_APP:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only channel=in_app is supported in this slice",
        )
    if schedule != AssignmentSchedule.ONCE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only schedule=once is supported in this slice",
        )
    if due_at is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="due_at is required for schedule=once",
        )

    questionnaire = questionnaires_repo.get_questionnaire_by_id(db, questionnaire_id)
    if questionnaire is None or questionnaire.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if questionnaires_repo.has_successor(db, questionnaire.id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Questionnaire is not the latest version",
        )

    target_player_ids = _resolve_target_player_ids(
        db,
        principal=principal,
        organization_id=org_id,
        target_type=target_type,
        team_id=team_id,
        player_ids=player_ids or [],
    )
    if not target_player_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No players to assign",
        )

    snapshot = copy.deepcopy(questionnaire.questions)
    now = datetime.now(UTC)
    assignment = assignments_repo.create_assignment(
        db,
        organization_id=org_id,
        questionnaire_id=questionnaire.id,
        questions_snapshot=snapshot,
        created_by=principal.user_id,
        target_type=target_type,
        team_id=team_id if target_type == AssignmentTargetType.TEAM else None,
        schedule=AssignmentSchedule.ONCE,
        due_at=due_at,
        channel=AssignmentChannel.IN_APP,
    )

    if questionnaire.locked_at is None:
        questionnaire.locked_at = now

    for player_id in target_player_ids:
        assignments_repo.add_assignment_target(
            db, assignment_id=assignment.id, user_id=player_id
        )
        assignments_repo.create_occurrence(
            db,
            assignment_id=assignment.id,
            organization_id=org_id,
            player_id=player_id,
            window_start=now,
            due_at=due_at,
        )

    db.commit()
    db.refresh(assignment)
    count = assignments_repo.count_occurrences_for_assignment(db, assignment.id)
    return assignment, count


def _resolve_target_player_ids(
    db: Session,
    *,
    principal: Principal,
    organization_id: uuid.UUID,
    target_type: AssignmentTargetType,
    team_id: uuid.UUID | None,
    player_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    if target_type == AssignmentTargetType.TEAM:
        assert team_id is not None
        team = teams_repo.get_team_by_id(db, team_id)
        if (
            team is None
            or team.organization_id != organization_id
            or not principal.is_on_team(team_id)
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
            )
        return assignments_repo.list_player_ids_on_team(
            db, team_id=team_id, organization_id=organization_id
        )

    resolved: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    for player_id in player_ids:
        if player_id in seen:
            continue
        seen.add(player_id)
        if not _is_player_in_org(db, user_id=player_id, organization_id=organization_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
            )
        if not assignments_repo.player_shares_team_with_coach(
            db,
            coach_user_id=principal.user_id,
            player_user_id=player_id,
            organization_id=organization_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
            )
        resolved.append(player_id)
    return resolved


def _is_player_in_org(
    db: Session, *, user_id: uuid.UUID, organization_id: uuid.UUID
) -> bool:
    for membership in users_repo.list_memberships_for_user(db, user_id):
        if (
            membership.organization_id == organization_id
            and membership.role == MembershipRole.PLAYER
            and membership.status
            in (MembershipStatus.INVITED, MembershipStatus.ACTIVE)
        ):
            return True
    return False


def list_occurrences_for_player(
    db: Session, *, principal: Principal
) -> list[dict[str, Any]]:
    rows = assignments_repo.list_occurrence_details_for_player(db, principal.user_id)
    return [
        {
            "id": occurrence.id,
            "assignment_id": occurrence.assignment_id,
            "organization_id": occurrence.organization_id,
            "player_id": occurrence.player_id,
            "status": occurrence.status,
            "due_at": occurrence.due_at,
            "window_start": occurrence.window_start,
            "questionnaire_name": questionnaire_name or "Questionnaire",
            "questions": assignment.questions_snapshot,
            "created_at": occurrence.created_at,
        }
        for occurrence, assignment, questionnaire_name in rows
    ]


def get_player_history(db: Session, *, principal: Principal) -> PlayerHistoryOut:
    rows = assignments_repo.list_player_submissions(db, player_id=principal.user_id)
    submissions = [
        PlayerHistoryItemOut(
            occurrence_id=occurrence.id,
            assignment_id=assignment.id,
            questionnaire_id=assignment.questionnaire_id,
            questionnaire_name=questionnaire_name or "Questionnaire",
            status=occurrence.status,
            channel=response.channel,
            submitted_at=response.submitted_at,
            due_at=occurrence.due_at,
            answers=response.answers,
            questions_snapshot=response.questions_snapshot,
        )
        for occurrence, assignment, questionnaire_name, response in rows
    ]
    return PlayerHistoryOut(
        submissions=submissions,
        rating_trends=_build_rating_trends(submissions),
    )


def _build_rating_trends(
    submissions: list[PlayerHistoryItemOut],
) -> list[RatingTrendOut]:
    # Walk oldest → newest so "last five" keeps the most recent values.
    chronological = list(reversed(submissions))
    series: dict[str, RatingTrendOut] = {}
    for item in chronological:
        questions_by_id = {
            q["id"]: q for q in item.questions_snapshot if isinstance(q, dict)
        }
        for qid, value in item.answers.items():
            question = questions_by_id.get(qid)
            if question is None or question.get("type") != "rating":
                continue
            if not isinstance(value, int) or isinstance(value, bool):
                continue
            trend = series.get(qid)
            if trend is None:
                trend = RatingTrendOut(
                    question_id=qid,
                    prompt=question.get("prompt", qid),
                    values=[],
                )
                series[qid] = trend
            trend.values.append(value)
            if len(trend.values) > 5:
                trend.values = trend.values[-5:]
    return list(series.values())


def submit_occurrence_response(
    db: Session,
    *,
    principal: Principal,
    occurrence_id: uuid.UUID,
    answers: dict[str, Any],
) -> Response:
    occurrence = assignments_repo.get_occurrence_by_id(db, occurrence_id)
    if occurrence is None or occurrence.player_id != principal.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    existing = assignments_repo.get_response_for_occurrence(db, occurrence.id)
    if existing is not None or occurrence.status == OccurrenceStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Occurrence already has a response",
        )

    assignment = assignments_repo.get_assignment_by_id(db, occurrence.assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    try:
        normalized = validate_answers(
            questions_snapshot=assignment.questions_snapshot,
            answers=answers,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    try:
        response = assignments_repo.create_response(
            db,
            occurrence_id=occurrence.id,
            organization_id=occurrence.organization_id,
            player_id=occurrence.player_id,
            channel=AssignmentChannel.IN_APP,
            answers=normalized,
            questions_snapshot=copy.deepcopy(assignment.questions_snapshot),
        )
        occurrence.status = OccurrenceStatus.COMPLETED
        db.commit()
        db.refresh(response)
        return response
    except IntegrityError as exc:
        db.rollback()
        if (
            assignments_repo.get_response_for_occurrence(db, occurrence_id)
            is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Occurrence already has a response",
            ) from exc
        raise
