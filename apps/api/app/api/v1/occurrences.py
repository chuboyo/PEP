from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.dependencies import require_coach
from app.core.principal import Principal
from app.db.session import get_db
from app.services import reminders as reminders_service

router = APIRouter(tags=["occurrences"])


@router.post("/occurrences/{occurrence_id}/remind", status_code=204)
def remind_occurrence(
    occurrence_id: uuid.UUID,
    principal: Principal = Depends(require_coach),
    db: Session = Depends(get_db),
) -> Response:
    reminders_service.remind_occurrence(
        db, principal=principal, occurrence_id=occurrence_id
    )
    return Response(status_code=204)
