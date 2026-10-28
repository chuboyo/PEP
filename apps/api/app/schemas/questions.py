from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter, field_validator, model_validator

QUESTION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,40}$")


class ChoiceOption(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1, max_length=24)

    @field_validator("id")
    @classmethod
    def validate_option_id(cls, value: str) -> str:
        if not QUESTION_ID_PATTERN.match(value):
            raise ValueError(
                "option id must match ^[a-z][a-z0-9_]{0,40}$"
            )
        return value


class QuestionBase(BaseModel):
    id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    required: bool = True

    @field_validator("id")
    @classmethod
    def validate_question_id(cls, value: str) -> str:
        if not QUESTION_ID_PATTERN.match(value):
            raise ValueError(
                "question id must match ^[a-z][a-z0-9_]{0,40}$"
            )
        return value


class YesNoQuestion(QuestionBase):
    type: Literal["yes_no"]


class RatingQuestion(QuestionBase):
    type: Literal["rating"]
    min: Literal[1] = 1
    max: Literal[5] = 5


class SingleChoiceQuestion(QuestionBase):
    type: Literal["single_choice"]
    options: list[ChoiceOption] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def unique_option_ids(self) -> SingleChoiceQuestion:
        ids = [o.id for o in self.options]
        if len(ids) != len(set(ids)):
            raise ValueError("option ids must be unique")
        return self


class ShortTextQuestion(QuestionBase):
    type: Literal["short_text"]
    max_length: int = Field(default=280, ge=1, le=2000)


Question = Annotated[
    YesNoQuestion | RatingQuestion | SingleChoiceQuestion | ShortTextQuestion,
    Field(discriminator="type"),
]

_questions_adapter = TypeAdapter(list[Question])


def validate_questions(questions: list[dict]) -> list[dict]:
    """Validate and normalize a questions list. Raises ValidationError on failure."""
    parsed = _questions_adapter.validate_python(questions)
    ids = [q.id for q in parsed]
    if len(ids) != len(set(ids)):
        raise ValueError("question ids must be unique within a questionnaire")
    return [q.model_dump() for q in parsed]
