from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_principal, require_coach, require_player
from app.core.principal import Principal
from app.db.session import get_db
from app.schemas.routines import (
    RoutineAssignmentOut,
    RoutineCreate,
    RoutineOut,
    RoutineStatusUpdate,
)
from app.services import routines as routines_service

router = APIRouter(tags=["routines"])


@router.post("/routines", response_model=RoutineOut)
def create_routine(
    body: RoutineCreate,
    principal: Principal = Depends(require_coach),
    db: Session = Depends(get_db),
) -> RoutineOut:
    routine, count = routines_service.create_routine(
        db, principal=principal, body=body
    )
    return RoutineOut(
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
        assignment_count=count,
    )


@router.get("/routines", response_model=list[dict[str, Any]])
def list_routines(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = routines_service.list_routines_for_principal(db, principal=principal)
    return [row.model_dump(mode="json") for row in rows]


@router.post(
    "/player/routines/{assignment_id}/status",
    response_model=RoutineAssignmentOut,
)
def update_routine_status(
    assignment_id: uuid.UUID,
    body: RoutineStatusUpdate,
    principal: Principal = Depends(require_player),
    db: Session = Depends(get_db),
) -> RoutineAssignmentOut:
    return routines_service.update_assignment_status(
        db,
        principal=principal,
        assignment_id=assignment_id,
        new_status=body.status,
    )
