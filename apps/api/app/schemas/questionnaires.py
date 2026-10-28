from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QuestionnaireTemplateOut(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    description: str | None
    questions: list[dict[str, Any]]
    schema_version: int


class QuestionnaireCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    questions: list[dict[str, Any]]
    template_id: uuid.UUID | None = None


class QuestionnaireUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    questions: list[dict[str, Any]] | None = None


class QuestionnaireOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    template_id: uuid.UUID | None
    version: int
    supersedes_id: uuid.UUID | None
    name: str
    description: str | None
    questions: list[dict[str, Any]]
    schema_version: int
    created_by: uuid.UUID
    locked_at: datetime | None
    created_at: datetime
