from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.enums import (
    AssignmentChannel,
    AssignmentSchedule,
    AssignmentTargetType,
    OccurrenceStatus,
)


class AssignmentCreate(BaseModel):
    questionnaire_id: uuid.UUID
    target_type: AssignmentTargetType
    team_id: uuid.UUID | None = None
    player_ids: list[uuid.UUID] | None = None
    due_at: datetime | None = None
    channel: AssignmentChannel = AssignmentChannel.IN_APP
    schedule: AssignmentSchedule = AssignmentSchedule.ONCE

    @model_validator(mode="after")
    def validate_target_fields(self) -> AssignmentCreate:
        if self.target_type == AssignmentTargetType.TEAM and self.team_id is None:
            raise ValueError("team_id is required when target_type is team")
        if self.target_type == AssignmentTargetType.PLAYERS and not self.player_ids:
            raise ValueError("player_ids is required when target_type is players")
        return self


class AssignmentOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    questionnaire_id: uuid.UUID
    questions_snapshot: list[dict[str, Any]]
    created_by: uuid.UUID
    target_type: AssignmentTargetType
    team_id: uuid.UUID | None
    schedule: AssignmentSchedule
    due_at: datetime | None
    channel: AssignmentChannel
    created_at: datetime
    occurrence_count: int


class PlayerOccurrenceOut(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    organization_id: uuid.UUID
    player_id: uuid.UUID
    status: OccurrenceStatus
    due_at: datetime | None
    window_start: datetime
    questionnaire_name: str
    questions: list[dict[str, Any]]
    created_at: datetime


class OccurrenceResponseCreate(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)


class OccurrenceResponseOut(BaseModel):
    id: uuid.UUID
    occurrence_id: uuid.UUID
    organization_id: uuid.UUID
    player_id: uuid.UUID
    channel: AssignmentChannel
    answers: dict[str, Any]
    submitted_at: datetime
