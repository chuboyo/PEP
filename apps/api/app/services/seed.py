from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import PlatformRole, UserStatus
from app.repositories import users as users_repo

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
