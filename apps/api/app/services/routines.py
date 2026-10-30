from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.principal import Principal
from app.models import (
    MembershipRole,
    MembershipStatus,
    RoutineAssignmentStatus,
    TrainingRoutine,
)
from app.repositories import assignments as assignments_repo
from app.repositories import routines as routines_repo
from app.repositories import teams as teams_repo
from app.repositories import users as users_repo
from app.schemas.routines import (
    RoutineAssignmentOut,
    RoutineCreate,
    RoutineOut,
)


_FORWARD: dict[RoutineAssignmentStatus, RoutineAssignmentStatus] = {
    RoutineAssignmentStatus.NOT_STARTED: RoutineAssignmentStatus.IN_PROGRESS,
    RoutineAssignmentStatus.IN_PROGRESS: RoutineAssignmentStatus.COMPLETED,
}


def create_routine(
    db: Session, *, principal: Principal, body: RoutineCreate
) -> tuple[TrainingRoutine, int]:
    org_id = principal.active_coach_organization_id
    if org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if body.team_id is not None:
        team = teams_repo.get_team_by_id(db, body.team_id)
        if (
            team is None
            or team.organization_id != org_id
            or not principal.is_on_team(body.team_id)
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
            )
        player_ids = assignments_repo.list_player_ids_on_team(
            db, team_id=body.team_id, organization_id=org_id
        )
    else:
        player_ids = []
        seen: set[uuid.UUID] = set()
        for player_id in body.player_ids or []:
            if player_id in seen:
                continue
            seen.add(player_id)
            if not _is_player_in_org(db, user_id=player_id, organization_id=org_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
                )
            if not assignments_repo.player_shares_team_with_coach(
                db,
                coach_user_id=principal.user_id,
                player_user_id=player_id,
                organization_id=org_id,
            ):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
                )
            player_ids.append(player_id)

    if not player_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No players to assign",
        )

    routine = routines_repo.create_routine(
        db,
        organization_id=org_id,
        team_id=body.team_id,
        created_by=principal.user_id,
        name=body.name,
        description=body.description,
        objective=body.objective,
        exercises=[e.model_dump() for e in body.exercises],
        duration_minutes=body.duration_minutes,
        intensity=body.intensity,
        frequency=body.frequency,
        start_date=body.start_date,
        end_date=body.end_date,
        instructions=body.instructions,
    )
    for player_id in player_ids:
        routines_repo.create_assignment(
            db,
            routine_id=routine.id,
            player_id=player_id,
            organization_id=org_id,
        )
    db.commit()
    db.refresh(routine)
    count = routines_repo.count_assignments_for_routine(db, routine.id)
    return routine, count


def list_routines_for_principal(
    db: Session, *, principal: Principal
) -> list[RoutineOut] | list[RoutineAssignmentOut]:
    if principal.active_coach_organization_id is not None:
        org_id = principal.active_coach_organization_id
        routines = routines_repo.list_routines_for_coach(
            db, organization_id=org_id, team_ids=list(principal.team_ids)
        )
        return [
            RoutineOut(
                id=routine.id,
                organization_id=routine.organization_id,
                team_id=routine.team_id,
                created_by=routine.created_by,
                name=routine.name,
                description=routine.description,
                objective=routine.objective,
                exercises=routine.exercises,
                duration_minutes=routine.duration_minutes,
                intensity=routine.intensity,
                frequency=routine.frequency,
                start_date=routine.start_date,
                end_date=routine.end_date,
                instructions=routine.instructions,
                created_at=routine.created_at,
                assignment_count=routines_repo.count_assignments_for_routine(
                    db, routine.id
                ),
            )
            for routine in routines
        ]

    if any(
        m.status == "active" and m.role == MembershipRole.PLAYER.value
        for m in principal.memberships
    ):
        rows = routines_repo.list_assignments_for_player(
            db, player_id=principal.user_id
        )
        return [
            RoutineAssignmentOut(
                id=assignment.id,
                routine_id=routine.id,
                player_id=assignment.player_id,
                organization_id=assignment.organization_id,
                status=assignment.status,
                updated_at=assignment.updated_at,
                routine_name=routine.name,
                description=routine.description,
                objective=routine.objective,
                exercises=routine.exercises,
                duration_minutes=routine.duration_minutes,
                intensity=routine.intensity,
                frequency=routine.frequency,
                start_date=routine.start_date,
                end_date=routine.end_date,
                instructions=routine.instructions,
            )
            for assignment, routine in rows
        ]

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def update_assignment_status(
    db: Session,
    *,
    principal: Principal,
    assignment_id: uuid.UUID,
    new_status: RoutineAssignmentStatus,
) -> RoutineAssignmentOut:
    assignment = routines_repo.get_assignment_by_id(db, assignment_id)
    if assignment is None or assignment.player_id != principal.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    expected = _FORWARD.get(assignment.status)
    if expected is None or new_status != expected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid status transition",
        )

    routines_repo.touch_assignment(
        db,
        assignment,
        status=new_status,
        updated_at=datetime.now(UTC),
    )
    db.commit()
    db.refresh(assignment)

    routine = db.get(TrainingRoutine, assignment.routine_id)
    assert routine is not None
    return RoutineAssignmentOut(
        id=assignment.id,
        routine_id=routine.id,
        player_id=assignment.player_id,
        organization_id=assignment.organization_id,
        status=assignment.status,
        updated_at=assignment.updated_at,
        routine_name=routine.name,
        description=routine.description,
        objective=routine.objective,
        exercises=routine.exercises,
        duration_minutes=routine.duration_minutes,
        intensity=routine.intensity,
        frequency=routine.frequency,
        start_date=routine.start_date,
        end_date=routine.end_date,
        instructions=routine.instructions,
    )


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
