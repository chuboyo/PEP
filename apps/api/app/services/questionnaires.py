from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.principal import Principal
from app.models import Questionnaire, QuestionnaireTemplate
from app.repositories import questionnaires as questionnaires_repo
from app.schemas.questions import validate_questions

SCHEMA_VERSION = 1


def _require_coach_org(principal: Principal) -> uuid.UUID:
    org_id = principal.active_coach_organization_id
    if org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return org_id


def _validate_or_422(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        return validate_questions(questions)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def list_templates(db: Session, *, principal: Principal) -> list[QuestionnaireTemplate]:
    _require_coach_org(principal)
    return questionnaires_repo.list_templates(db)


def create_questionnaire(
    db: Session,
    *,
    principal: Principal,
    name: str,
    description: str | None,
    questions: list[dict[str, Any]],
    template_id: uuid.UUID | None,
) -> Questionnaire:
    org_id = _require_coach_org(principal)

    if template_id is not None:
        template = questionnaires_repo.get_template_by_id(db, template_id)
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
            )

    validated = _validate_or_422(questions)
    row = questionnaires_repo.create_questionnaire(
        db,
        organization_id=org_id,
        template_id=template_id,
        version=1,
        supersedes_id=None,
        name=name,
        description=description,
        questions=validated,
        schema_version=SCHEMA_VERSION,
        created_by=principal.user_id,
    )
    db.commit()
    db.refresh(row)
    return row


def list_questionnaires(
    db: Session, *, principal: Principal
) -> list[Questionnaire]:
    org_id = _require_coach_org(principal)
    return questionnaires_repo.list_latest_for_organization(db, org_id)


def get_questionnaire_for_coach(
    db: Session, *, principal: Principal, questionnaire_id: uuid.UUID
) -> Questionnaire:
    org_id = _require_coach_org(principal)
    row = questionnaires_repo.get_questionnaire_by_id(db, questionnaire_id)
    if row is None or row.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return row


def update_questionnaire(
    db: Session,
    *,
    principal: Principal,
    questionnaire_id: uuid.UUID,
    fields: dict[str, Any],
) -> Questionnaire:
    row = get_questionnaire_for_coach(
        db, principal=principal, questionnaire_id=questionnaire_id
    )

    new_name = fields["name"] if "name" in fields else row.name
    new_description = (
        fields["description"] if "description" in fields else row.description
    )
    if "questions" in fields:
        new_questions = _validate_or_422(fields["questions"])
    else:
        new_questions = row.questions

    if row.locked_at is None:
        if "name" in fields:
            row.name = new_name
        if "description" in fields:
            row.description = new_description
        if "questions" in fields:
            row.questions = new_questions
        db.commit()
        db.refresh(row)
        return row

    next_row = questionnaires_repo.create_questionnaire(
        db,
        organization_id=row.organization_id,
        template_id=row.template_id,
        version=row.version + 1,
        supersedes_id=row.id,
        name=new_name,
        description=new_description,
        questions=new_questions,
        schema_version=SCHEMA_VERSION,
        created_by=principal.user_id,
        locked_at=None,
    )
    db.commit()
    db.refresh(next_row)
    return next_row
