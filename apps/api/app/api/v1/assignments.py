from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_coach
from app.core.principal import Principal
from app.db.session import get_db
from app.schemas.assignments import AssignmentCreate, AssignmentOut
from app.services import assignments as assignments_service

router = APIRouter(tags=["assignments"])


@router.post("/assignments", response_model=AssignmentOut)
def create_assignment(
    body: AssignmentCreate,
    principal: Principal = Depends(require_coach),
    db: Session = Depends(get_db),
) -> AssignmentOut:
    assignment, count = assignments_service.create_assignment(
        db,
        principal=principal,
        questionnaire_id=body.questionnaire_id,
        target_type=body.target_type,
        team_id=body.team_id,
        player_ids=body.player_ids,
        due_at=body.due_at,
        channel=body.channel,
        schedule=body.schedule,
    )
    return AssignmentOut(
        id=assignment.id,
        organization_id=assignment.organization_id,
        questionnaire_id=assignment.questionnaire_id,
        questions_snapshot=assignment.questions_snapshot,
        created_by=assignment.created_by,
        target_type=assignment.target_type,
        team_id=assignment.team_id,
        schedule=assignment.schedule,
        due_at=assignment.due_at,
        channel=assignment.channel,
        created_at=assignment.created_at,
        occurrence_count=count,
    )
