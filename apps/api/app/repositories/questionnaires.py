from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, aliased

from app.models import Questionnaire, QuestionnaireTemplate


def list_templates(db: Session) -> list[QuestionnaireTemplate]:
    return list(
        db.scalars(
            select(QuestionnaireTemplate).order_by(QuestionnaireTemplate.key)
        ).all()
    )


def get_template_by_id(
    db: Session, template_id: uuid.UUID
) -> QuestionnaireTemplate | None:
    return db.get(QuestionnaireTemplate, template_id)


def get_template_by_key(db: Session, key: str) -> QuestionnaireTemplate | None:
    return db.scalar(
        select(QuestionnaireTemplate).where(QuestionnaireTemplate.key == key)
    )


def upsert_template(
    db: Session,
    *,
    key: str,
    name: str,
    description: str | None,
    questions: list[dict[str, Any]],
    schema_version: int,
) -> QuestionnaireTemplate:
    existing = get_template_by_key(db, key)
    if existing is not None:
        existing.name = name
        existing.description = description
        existing.questions = questions
        existing.schema_version = schema_version
        db.flush()
        return existing
    row = QuestionnaireTemplate(
        key=key,
        name=name,
        description=description,
        questions=questions,
        schema_version=schema_version,
    )
    db.add(row)
    db.flush()
    return row


def create_questionnaire(
    db: Session,
    *,
    organization_id: uuid.UUID,
    template_id: uuid.UUID | None,
    version: int,
    supersedes_id: uuid.UUID | None,
    name: str,
    description: str | None,
    questions: list[dict[str, Any]],
    schema_version: int,
    created_by: uuid.UUID,
    locked_at: datetime | None = None,
) -> Questionnaire:
    row = Questionnaire(
        organization_id=organization_id,
        template_id=template_id,
        version=version,
        supersedes_id=supersedes_id,
        name=name,
        description=description,
        questions=questions,
        schema_version=schema_version,
        created_by=created_by,
        locked_at=locked_at,
    )
    db.add(row)
    db.flush()
    return row


def get_questionnaire_by_id(
    db: Session, questionnaire_id: uuid.UUID
) -> Questionnaire | None:
    return db.get(Questionnaire, questionnaire_id)


def list_latest_for_organization(
    db: Session, organization_id: uuid.UUID
) -> list[Questionnaire]:
    Newer = aliased(Questionnaire)
    return list(
        db.scalars(
            select(Questionnaire)
            .where(
                Questionnaire.organization_id == organization_id,
                ~exists(select(1).where(Newer.supersedes_id == Questionnaire.id)),
            )
            .order_by(Questionnaire.name)
        ).all()
    )
