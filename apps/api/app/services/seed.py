from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import PlatformRole, UserStatus
from app.repositories import users as users_repo


def ensure_superadmin(db: Session) -> None:
    if users_repo.get_superadmin(db) is not None:
        return

    settings = get_settings()
    users_repo.create_user(
        db,
        email=settings.superadmin_email,
        name="Superadmin",
        password_hash=hash_password(settings.superadmin_password),
        status=UserStatus.ACTIVE,
        platform_role=PlatformRole.SUPERADMIN,
    )
    db.commit()
