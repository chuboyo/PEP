from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.principal import Principal
from app.models import OccurrenceStatus
from app.repositories import assignments as assignments_repo
from app.repositories import routines as routines_repo
from app.repositories import teams as teams_repo
from app.repositories import users as users_repo
from app.schemas.dashboard import (
    AttentionFlagOut,
    AttentionFlagType,
    DashboardPlayerRowOut,
    PlayerDetailOut,
    PlayerOccurrenceHistoryOut,
    QuestionStatOut,
    RoutineCountsOut,
    TeamDashboardOut,
)


def get_team_dashboard(
    db: Session,
    *,
    principal: Principal,
    team_id: uuid.UUID,
    questionnaire_id: uuid.UUID | None = None,
) -> TeamDashboardOut:
    team = teams_repo.get_team_by_id(db, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    org_id = principal.active_coach_organization_id
    assert org_id is not None

    roster_names = assignments_repo.list_roster_player_names(
        db, team_id=team_id, organization_id=org_id
    )
    roster_size = len(roster_names)
    routine_counts = RoutineCountsOut(
        **routines_repo.count_statuses_for_team_roster(
            db,
            organization_id=org_id,
            player_ids=list(roster_names.keys()),
        )
    )

    assignment = assignments_repo.get_latest_team_assignment(
        db, team_id=team_id, questionnaire_id=questionnaire_id
    )
    if assignment is None:
        return TeamDashboardOut(
            team_id=team_id,
            assignment_id=None,
            questionnaire_id=None,
            questionnaire_name=None,
            questions_snapshot=[],
            completion_count=0,
            roster_size=roster_size,
            question_stats=[],
            players=[],
            flags=[],
            routine_counts=routine_counts,
        )

    questionnaire_name = assignments_repo.get_questionnaire_name(
        db, assignment.questionnaire_id
    )
    rows = assignments_repo.list_assignment_player_rows(db, assignment_id=assignment.id)

    players: list[DashboardPlayerRowOut] = []
    completed_answers: list[dict[str, Any]] = []
    for occurrence, user, response in rows:
        if occurrence.player_id not in roster_names:
            continue
        submitted_at = response.submitted_at if response else None
        channel = response.channel if response else None
        answers = response.answers if response else None
        if occurrence.status == OccurrenceStatus.COMPLETED and answers is not None:
            completed_answers.append(answers)
        players.append(
            DashboardPlayerRowOut(
                player_id=user.id,
                name=user.name,
                status=occurrence.status,
                submitted_at=submitted_at,
                channel=channel,
                answers=answers,
            )
        )

    question_stats = _compute_question_stats(
        questions_snapshot=assignment.questions_snapshot,
        completed_answers=completed_answers,
    )
    flags = _compute_attention_flags(
        db,
        questionnaire_id=assignment.questionnaire_id,
        roster_names=roster_names,
    )

    return TeamDashboardOut(
        team_id=team_id,
        assignment_id=assignment.id,
        questionnaire_id=assignment.questionnaire_id,
        questionnaire_name=questionnaire_name,
        questions_snapshot=assignment.questions_snapshot,
        completion_count=len(completed_answers),
        roster_size=roster_size,
        question_stats=question_stats,
        players=players,
        flags=flags,
        routine_counts=routine_counts,
    )


def get_player_detail(
    db: Session,
    *,
    principal: Principal,
    player_id: uuid.UUID,
) -> PlayerDetailOut:
    org_id = principal.active_coach_organization_id
    if org_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    player = users_repo.get_user_by_id(db, player_id)
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if not assignments_repo.player_shares_team_with_coach(
        db,
        coach_user_id=principal.user_id,
        player_user_id=player_id,
        organization_id=org_id,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    history = assignments_repo.list_player_occurrence_history(
        db, player_id=player_id, organization_id=org_id
    )
    occurrences = [
        PlayerOccurrenceHistoryOut(
            occurrence_id=occurrence.id,
            assignment_id=assignment.id,
            questionnaire_id=assignment.questionnaire_id,
            questionnaire_name=questionnaire_name or "Questionnaire",
            status=occurrence.status,
            due_at=occurrence.due_at,
            submitted_at=response.submitted_at if response else None,
            channel=response.channel if response else None,
            answers=response.answers if response else None,
            questions_snapshot=(
                response.questions_snapshot
                if response
                else assignment.questions_snapshot
            ),
        )
        for occurrence, assignment, questionnaire_name, response in history
    ]
    return PlayerDetailOut(
        id=player.id,
        name=player.name,
        email=player.email,
        occurrences=occurrences,
    )


def _compute_question_stats(
    *,
    questions_snapshot: list[dict[str, Any]],
    completed_answers: list[dict[str, Any]],
) -> list[QuestionStatOut]:
    stats: list[QuestionStatOut] = []
    for question in questions_snapshot:
        qid = question["id"]
        qtype = question["type"]
        prompt = question.get("prompt", qid)
        if qtype == "rating":
            values = [
                answers[qid]
                for answers in completed_answers
                if qid in answers and isinstance(answers[qid], int)
            ]
            average = (sum(values) / len(values)) if values else None
            stats.append(
                QuestionStatOut(
                    question_id=qid,
                    question_type=qtype,
                    prompt=prompt,
                    average=average,
                )
            )
        elif qtype == "yes_no":
            yes_count = sum(
                1
                for answers in completed_answers
                if answers.get(qid) is True
            )
            stats.append(
                QuestionStatOut(
                    question_id=qid,
                    question_type=qtype,
                    prompt=prompt,
                    yes_count=yes_count,
                )
            )
        elif qtype == "single_choice":
            option_counts: dict[str, int] = {
                opt["id"]: 0 for opt in question.get("options", [])
            }
            for answers in completed_answers:
                value = answers.get(qid)
                if isinstance(value, str) and value in option_counts:
                    option_counts[value] += 1
            stats.append(
                QuestionStatOut(
                    question_id=qid,
                    question_type=qtype,
                    prompt=prompt,
                    option_counts=option_counts,
                )
            )
    return stats


def _compute_attention_flags(
    db: Session,
    *,
    questionnaire_id: uuid.UUID,
    roster_names: dict[uuid.UUID, str],
) -> list[AttentionFlagOut]:
    player_ids = list(roster_names.keys())
    history = assignments_repo.list_questionnaire_history_for_players(
        db, questionnaire_id=questionnaire_id, player_ids=player_ids
    )

    by_player: dict[uuid.UUID, list[tuple[Any, Any]]] = defaultdict(list)
    for occurrence, response in history:
        by_player[occurrence.player_id].append((occurrence, response))

    now = datetime.now(UTC)
    flags: list[AttentionFlagOut] = []
    for player_id, rows in by_player.items():
        player_name = roster_names[player_id]

        # Missed streak: last two already-due occurrences have no completed
        # response. Future due_at rows are ignored so upcoming assigns do not
        # flag non-responders early.
        already_due = [
            (occurrence, response)
            for occurrence, response in rows
            if occurrence.due_at is not None and occurrence.due_at <= now
        ]
        last_two_due = already_due[:2]
        if len(last_two_due) == 2 and all(
            response is None or occurrence.status != OccurrenceStatus.COMPLETED
            for occurrence, response in last_two_due
        ):
            flags.append(
                AttentionFlagOut(
                    type=AttentionFlagType.MISSED_STREAK,
                    player_id=player_id,
                    player_name=player_name,
                )
            )

        # High rating streak: latest two completed both have rating >= 4
        # on the same question id.
        completed = [
            (occurrence, response)
            for occurrence, response in rows
            if response is not None
            and occurrence.status == OccurrenceStatus.COMPLETED
        ]
        # Re-sort completed by submitted_at desc for consecutive completed.
        completed.sort(
            key=lambda item: item[1].submitted_at,
            reverse=True,
        )
        if len(completed) >= 2:
            _, newer = completed[0]
            _, older = completed[1]
            newer_answers = newer.answers or {}
            older_answers = older.answers or {}
            shared_ids = set(newer_answers) & set(older_answers)
            for qid in sorted(shared_ids):
                newer_val = newer_answers[qid]
                older_val = older_answers[qid]
                if (
                    isinstance(newer_val, int)
                    and isinstance(older_val, int)
                    and newer_val >= 4
                    and older_val >= 4
                ):
                    flags.append(
                        AttentionFlagOut(
                            type=AttentionFlagType.HIGH_RATING_STREAK,
                            player_id=player_id,
                            player_name=player_name,
                            question_id=qid,
                        )
                    )

    flags.sort(key=lambda f: (f.type.value, f.player_name, f.question_id or ""))
    return flags
