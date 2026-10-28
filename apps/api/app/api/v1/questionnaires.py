from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_coach
from app.core.principal import Principal
from app.db.session import get_db
from app.schemas.questionnaires import (
    QuestionnaireCreate,
    QuestionnaireOut,
    QuestionnaireTemplateOut,
    QuestionnaireUpdate,
)
from app.services import questionnaires as questionnaires_service

router = APIRouter(tags=["questionnaires"])


@router.get("/questionnaire-templates", response_model=list[QuestionnaireTemplateOut])
def list_templates(
    principal: Principal = Depends(require_coach),
    db: Session = Depends(get_db),
) -> list[QuestionnaireTemplateOut]:
    templates = questionnaires_service.list_templates(db, principal=principal)
    return [
        QuestionnaireTemplateOut(
            id=t.id,
            key=t.key,
            name=t.name,
            description=t.description,
            questions=t.questions,
            schema_version=t.schema_version,
        )
        for t in templates
    ]


@router.post("/questionnaires", response_model=QuestionnaireOut)
def create_questionnaire(
    body: QuestionnaireCreate,
    principal: Principal = Depends(require_coach),
    db: Session = Depends(get_db),
) -> QuestionnaireOut:
    row = questionnaires_service.create_questionnaire(
        db,
        principal=principal,
        name=body.name,
        description=body.description,
        questions=body.questions,
        template_id=body.template_id,
    )
    return QuestionnaireOut.model_validate(row, from_attributes=True)


@router.get("/questionnaires", response_model=list[QuestionnaireOut])
def list_questionnaires(
    principal: Principal = Depends(require_coach),
    db: Session = Depends(get_db),
) -> list[QuestionnaireOut]:
    rows = questionnaires_service.list_questionnaires(db, principal=principal)
    return [
        QuestionnaireOut.model_validate(row, from_attributes=True) for row in rows
    ]


@router.patch("/questionnaires/{questionnaire_id}", response_model=QuestionnaireOut)
def update_questionnaire(
    questionnaire_id: uuid.UUID,
    body: QuestionnaireUpdate,
    principal: Principal = Depends(require_coach),
    db: Session = Depends(get_db),
) -> QuestionnaireOut:
    row = questionnaires_service.update_questionnaire(
        db,
        principal=principal,
        questionnaire_id=questionnaire_id,
        fields=body.model_dump(exclude_unset=True),
    )
    return QuestionnaireOut.model_validate(row, from_attributes=True)
