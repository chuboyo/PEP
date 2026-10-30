from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.enums import RoutineAssignmentStatus


class ExerciseItem(BaseModel):
    name: str = Field(min_length=1)
    duration_minutes: int = Field(ge=1)


class RoutineCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    exercises: list[ExerciseItem] = Field(min_length=1)
    duration_minutes: int = Field(ge=1)
    intensity: str | None = None
    frequency: str | None = None
    start_date: date
    end_date: date | None = None
    instructions: str | None = None
    team_id: uuid.UUID | None = None
    player_ids: list[uuid.UUID] | None = None

    @model_validator(mode="after")
    def validate_target(self) -> RoutineCreate:
        has_team = self.team_id is not None
        has_players = bool(self.player_ids)
        if has_team == has_players:
            raise ValueError("Provide exactly one of team_id or player_ids")
        return self


class RoutineOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    team_id: uuid.UUID | None
    created_by: uuid.UUID
    name: str
    description: str
    objective: str
    exercises: list[dict[str, Any]]
    duration_minutes: int
    intensity: str | None
    frequency: str | None
    start_date: date
    end_date: date | None
    instructions: str | None
    created_at: datetime
    assignment_count: int


class RoutineAssignmentOut(BaseModel):
    id: uuid.UUID
    routine_id: uuid.UUID
    player_id: uuid.UUID
    organization_id: uuid.UUID
    status: RoutineAssignmentStatus
    updated_at: datetime
    routine_name: str
    description: str
    objective: str
    exercises: list[dict[str, Any]]
    duration_minutes: int
    intensity: str | None
    frequency: str | None
    start_date: date
    end_date: date | None
    instructions: str | None


class RoutineStatusUpdate(BaseModel):
    status: RoutineAssignmentStatus
