from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import AssignmentChannel, OccurrenceStatus


class AttentionFlagType(str, enum.Enum):
    HIGH_RATING_STREAK = "high_rating_streak"
    MISSED_STREAK = "missed_streak"


class QuestionStatOut(BaseModel):
    question_id: str
    question_type: str
    prompt: str
    average: float | None = None
    yes_count: int | None = None
    option_counts: dict[str, int] | None = None


class DashboardPlayerRowOut(BaseModel):
    player_id: uuid.UUID
    name: str
    status: OccurrenceStatus
    submitted_at: datetime | None = None
    channel: AssignmentChannel | None = None
    answers: dict[str, Any] | None = None


class AttentionFlagOut(BaseModel):
    type: AttentionFlagType
    player_id: uuid.UUID
    player_name: str
    question_id: str | None = None


class RoutineCountsOut(BaseModel):
    assigned: int
    in_progress: int
    completed: int


class TeamDashboardOut(BaseModel):
    team_id: uuid.UUID
    assignment_id: uuid.UUID | None
    questionnaire_id: uuid.UUID | None
    questionnaire_name: str | None
    questions_snapshot: list[dict[str, Any]]
    completion_count: int
    roster_size: int
    question_stats: list[QuestionStatOut]
    players: list[DashboardPlayerRowOut]
    flags: list[AttentionFlagOut]
    routine_counts: RoutineCountsOut


class PlayerOccurrenceHistoryOut(BaseModel):
    occurrence_id: uuid.UUID
    assignment_id: uuid.UUID
    questionnaire_id: uuid.UUID
    questionnaire_name: str
    status: OccurrenceStatus
    due_at: datetime | None
    submitted_at: datetime | None
    channel: AssignmentChannel | None
    answers: dict[str, Any] | None
    questions_snapshot: list[dict[str, Any]]


class PlayerDetailOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    occurrences: list[PlayerOccurrenceHistoryOut]
