from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_principal
from app.core.principal import Principal
from app.db.session import get_db
from app.schemas.dashboard import PlayerDetailOut
from app.services import dashboard as dashboard_service

router = APIRouter(tags=["players"])


@router.get("/players/{player_id}", response_model=PlayerDetailOut)
def get_player(
    player_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> PlayerDetailOut:
    # Club admin and other non-coach callers get 404 (not 403) per Slice 6.
    return dashboard_service.get_player_detail(
        db, principal=principal, player_id=player_id
    )
