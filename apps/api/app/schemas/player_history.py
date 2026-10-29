from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import AssignmentChannel, OccurrenceStatus


class PlayerHistoryItemOut(BaseModel):
    occurrence_id: uuid.UUID
    assignment_id: uuid.UUID
    questionnaire_id: uuid.UUID
    questionnaire_name: str
    status: OccurrenceStatus
    channel: AssignmentChannel | None
    submitted_at: datetime
    due_at: datetime | None
    answers: dict[str, Any]
    questions_snapshot: list[dict[str, Any]]


class RatingTrendOut(BaseModel):
    question_id: str
    prompt: str
    values: list[int]


class PlayerHistoryOut(BaseModel):
    submissions: list[PlayerHistoryItemOut]
    rating_trends: list[RatingTrendOut]
