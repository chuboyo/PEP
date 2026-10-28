from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.schemas.questions import _questions_adapter


def validate_answers(
    *,
    questions_snapshot: list[dict[str, Any]],
    answers: dict[str, Any],
) -> dict[str, Any]:
    """Validate answers against a questions snapshot. Raises ValueError on failure."""
    try:
        questions = _questions_adapter.validate_python(questions_snapshot)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    known_ids = {q.id for q in questions}
    unknown = set(answers) - known_ids
    if unknown:
        raise ValueError(f"Unknown question ids: {sorted(unknown)}")

    normalized: dict[str, Any] = {}
    for question in questions:
        if question.id not in answers:
            if question.required:
                raise ValueError(f"Missing required answer for '{question.id}'")
            continue

        value = answers[question.id]
        if question.type == "yes_no":
            if not isinstance(value, bool):
                raise ValueError(f"Answer for '{question.id}' must be a boolean")
            normalized[question.id] = value
        elif question.type == "rating":
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"Answer for '{question.id}' must be an integer")
            if value < question.min or value > question.max:
                raise ValueError(
                    f"Answer for '{question.id}' must be between "
                    f"{question.min} and {question.max}"
                )
            normalized[question.id] = value
        elif question.type == "single_choice":
            option_ids = {o.id for o in question.options}
            if not isinstance(value, str) or value not in option_ids:
                raise ValueError(f"Answer for '{question.id}' must be a valid option id")
            normalized[question.id] = value
        elif question.type == "short_text":
            if not isinstance(value, str):
                raise ValueError(f"Answer for '{question.id}' must be a string")
            if question.required and not value.strip():
                raise ValueError(f"Missing required answer for '{question.id}'")
            if len(value) > question.max_length:
                raise ValueError(
                    f"Answer for '{question.id}' exceeds max length "
                    f"{question.max_length}"
                )
            normalized[question.id] = value
        else:
            raise ValueError(f"Unsupported question type for '{question.id}'")

    return normalized
