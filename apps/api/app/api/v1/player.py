from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_player
from app.core.principal import Principal
from app.db.session import get_db
from app.schemas.assignments import (
    OccurrenceResponseCreate,
    OccurrenceResponseOut,
    PlayerOccurrenceOut,
)
from app.services import assignments as assignments_service

router = APIRouter(tags=["player"])


@router.get("/player/occurrences", response_model=list[PlayerOccurrenceOut])
def list_my_occurrences(
    principal: Principal = Depends(require_player),
    db: Session = Depends(get_db),
) -> list[PlayerOccurrenceOut]:
    rows = assignments_service.list_occurrences_for_player(db, principal=principal)
    return [PlayerOccurrenceOut(**row) for row in rows]


@router.post(
    "/player/occurrences/{occurrence_id}/responses",
    response_model=OccurrenceResponseOut,
)
def submit_occurrence_response(
    occurrence_id: uuid.UUID,
    body: OccurrenceResponseCreate,
    principal: Principal = Depends(require_player),
    db: Session = Depends(get_db),
) -> OccurrenceResponseOut:
    response = assignments_service.submit_occurrence_response(
        db,
        principal=principal,
        occurrence_id=occurrence_id,
        answers=body.answers,
    )
    return OccurrenceResponseOut(
        id=response.id,
        occurrence_id=response.occurrence_id,
        organization_id=response.organization_id,
        player_id=response.player_id,
        channel=response.channel,
        answers=response.answers,
        submitted_at=response.submitted_at,
    )
