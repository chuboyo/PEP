from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    RoutineAssignment,
    RoutineAssignmentStatus,
    TrainingRoutine,
)


def create_routine(
    db: Session,
    *,
    organization_id: uuid.UUID,
    team_id: uuid.UUID | None,
    created_by: uuid.UUID,
    name: str,
    description: str,
    objective: str,
    exercises: list[dict[str, Any]],
    duration_minutes: int,
    intensity: str | None,
    frequency: str | None,
    start_date: date,
    end_date: date | None,
    instructions: str | None,
) -> TrainingRoutine:
    row = TrainingRoutine(
        organization_id=organization_id,
        team_id=team_id,
        created_by=created_by,
        name=name,
        description=description,
        objective=objective,
        exercises=exercises,
        duration_minutes=duration_minutes,
        intensity=intensity,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        instructions=instructions,
    )
    db.add(row)
    db.flush()
    return row


def create_assignment(
    db: Session,
    *,
    routine_id: uuid.UUID,
    player_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> RoutineAssignment:
    row = RoutineAssignment(
        routine_id=routine_id,
        player_id=player_id,
        organization_id=organization_id,
        status=RoutineAssignmentStatus.NOT_STARTED,
    )
    db.add(row)
    db.flush()
    return row


def count_assignments_for_routine(db: Session, routine_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(RoutineAssignment)
            .where(RoutineAssignment.routine_id == routine_id)
        )
        or 0
    )


def list_routines_for_coach(
    db: Session,
    *,
    organization_id: uuid.UUID,
    team_ids: list[uuid.UUID],
) -> list[TrainingRoutine]:
    if not team_ids:
        return list(
            db.scalars(
                select(TrainingRoutine)
                .where(
                    TrainingRoutine.organization_id == organization_id,
                    TrainingRoutine.team_id.is_(None),
                )
                .order_by(TrainingRoutine.created_at.desc())
            ).all()
        )
    return list(
        db.scalars(
            select(TrainingRoutine)
            .where(
                TrainingRoutine.organization_id == organization_id,
                (
                    TrainingRoutine.team_id.is_(None)
                    | TrainingRoutine.team_id.in_(team_ids)
                ),
            )
            .order_by(TrainingRoutine.created_at.desc())
        ).all()
    )


def list_assignments_for_player(
    db: Session, *, player_id: uuid.UUID
) -> list[tuple[RoutineAssignment, TrainingRoutine]]:
    rows = db.execute(
        select(RoutineAssignment, TrainingRoutine)
        .join(TrainingRoutine, TrainingRoutine.id == RoutineAssignment.routine_id)
        .where(RoutineAssignment.player_id == player_id)
        .order_by(RoutineAssignment.updated_at.desc())
    ).all()
    return [(assignment, routine) for assignment, routine in rows]


def get_assignment_by_id(
    db: Session, assignment_id: uuid.UUID
) -> RoutineAssignment | None:
    return db.get(RoutineAssignment, assignment_id)


def count_statuses_for_team_roster(
    db: Session,
    *,
    organization_id: uuid.UUID,
    player_ids: list[uuid.UUID],
) -> dict[str, int]:
    if not player_ids:
        return {"assigned": 0, "in_progress": 0, "completed": 0}
    rows = db.execute(
        select(RoutineAssignment.status, func.count())
        .where(
            RoutineAssignment.organization_id == organization_id,
            RoutineAssignment.player_id.in_(player_ids),
        )
        .group_by(RoutineAssignment.status)
    ).all()
    counts = {"assigned": 0, "in_progress": 0, "completed": 0}
    total = 0
    for status, count in rows:
        total += int(count)
        if status == RoutineAssignmentStatus.IN_PROGRESS:
            counts["in_progress"] = int(count)
        elif status == RoutineAssignmentStatus.COMPLETED:
            counts["completed"] = int(count)
    counts["assigned"] = total
    return counts


def touch_assignment(
    db: Session,
    assignment: RoutineAssignment,
    *,
    status: RoutineAssignmentStatus,
    updated_at: datetime,
) -> RoutineAssignment:
    assignment.status = status
    assignment.updated_at = updated_at
    db.flush()
    return assignment
