from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import PlatformRole, UserStatus
from app.repositories import questionnaires as questionnaires_repo
from app.repositories import users as users_repo

SCHEMA_VERSION = 1


def _rating(qid: str, prompt: str) -> dict[str, Any]:
    return {
        "id": qid,
        "prompt": prompt,
        "type": "rating",
        "min": 1,
        "max": 5,
        "required": True,
    }


QUESTIONNAIRE_TEMPLATES: list[dict[str, Any]] = [
    {
        "key": "daily_readiness",
        "name": "Daily Readiness",
        "description": "Quick morning check-in before training.",
        "questions": [
            _rating("sleep", "How did you sleep?"),
            _rating("soreness", "How sore do you feel?"),
            _rating("mood", "How is your mood?"),
            _rating("readiness", "How ready are you to train?"),
        ],
    },
    {
        "key": "weekly_wellness",
        "name": "Weekly Wellness",
        "description": "End-of-week wellness summary.",
        "questions": [
            _rating("fatigue", "Overall fatigue this week?"),
            _rating("stress", "Overall stress this week?"),
            _rating("sleep_quality", "Sleep quality this week?"),
            _rating("motivation", "Motivation this week?"),
        ],
    },
    {
        "key": "post_match_recovery",
        "name": "Post-Match Recovery",
        "description": "Recovery check after a match.",
        "questions": [
            _rating("match_load", "How hard was the match?"),
            _rating("muscle_soreness", "Muscle soreness now?"),
            _rating("energy", "Energy level now?"),
            _rating("recovery", "How well recovered do you feel?"),
        ],
    },
    {
        "key": "training_load",
        "name": "Training Load",
        "description": "Session RPE and load check.",
        "questions": [
            _rating("session_rpe", "How hard was the session?"),
            _rating("duration_feel", "How long did it feel?"),
            _rating("technical", "Technical quality today?"),
            _rating("enjoyment", "How much did you enjoy it?"),
        ],
    },
]

MIN_SUPERADMIN_PASSWORD_LENGTH = 12

# Published examples / common weak values — never accept for manual prod seed.
_FORBIDDEN_PASSWORDS = frozenset(
    {
        "changeme-superadmin",
        "changeme",
        "password",
        "password123",
        "superadmin",
        "admin",
        "admin123",
    }
)


class SeedError(ValueError):
    """Invalid seed input or conflict."""


def validate_superadmin_password(password: str) -> None:
    if len(password) < MIN_SUPERADMIN_PASSWORD_LENGTH:
        raise SeedError(
            f"Password must be at least {MIN_SUPERADMIN_PASSWORD_LENGTH} characters."
        )
    if password.lower() in _FORBIDDEN_PASSWORDS or password in _FORBIDDEN_PASSWORDS:
        raise SeedError("Password is too weak or matches a published example value.")


def ensure_superadmin(db: Session) -> None:
    """Create the Superadmin from settings if none exists.

    Used by opt-in startup seeding and tests. Does not enforce strong-password
    rules — use create_superadmin / validate_superadmin_password for prod.
    Refuses an empty password so startup cannot leave an unusable Superadmin.
    """
    if users_repo.get_superadmin(db) is not None:
        return

    settings = get_settings()
    password = settings.superadmin_password
    if not password.strip():
        raise SeedError(
            "SUPERADMIN_PASSWORD is empty; set a password or use "
            "`python -m scripts.create_superadmin`."
        )
    users_repo.create_user(
        db,
        email=settings.superadmin_email,
        name="Superadmin",
        password_hash=hash_password(password),
        status=UserStatus.ACTIVE,
        platform_role=PlatformRole.SUPERADMIN,
    )
    db.commit()


def create_superadmin(db: Session, *, email: str, password: str) -> None:
    """One-shot Superadmin creation with a strong password. Fails if one exists."""
    if users_repo.get_superadmin(db) is not None:
        raise SeedError("A Superadmin already exists.")
    validate_superadmin_password(password)
    users_repo.create_user(
        db,
        email=email,
        name="Superadmin",
        password_hash=hash_password(password),
        status=UserStatus.ACTIVE,
        platform_role=PlatformRole.SUPERADMIN,
    )
    db.commit()


def ensure_questionnaire_templates(db: Session) -> None:
    """Upsert the four platform questionnaire templates by key."""
    for template in QUESTIONNAIRE_TEMPLATES:
        questionnaires_repo.upsert_template(
            db,
            key=template["key"],
            name=template["name"],
            description=template["description"],
            questions=template["questions"],
            schema_version=SCHEMA_VERSION,
        )
    db.commit()
