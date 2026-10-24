import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories import users as users_repo
from app.services.seed import (
    SeedError,
    create_superadmin,
    ensure_superadmin,
    validate_superadmin_password,
)


def test_validate_superadmin_password_rejects_short() -> None:
    with pytest.raises(SeedError, match="at least 12"):
        validate_superadmin_password("short")


def test_validate_superadmin_password_rejects_published_default() -> None:
    with pytest.raises(SeedError, match="too weak"):
        validate_superadmin_password("changeme-superadmin")


def test_create_superadmin_requires_strong_password(db: Session) -> None:
    with pytest.raises(SeedError, match="too weak"):
        create_superadmin(
            db,
            email="admin@example.com",
            password="changeme-superadmin",
        )
    assert users_repo.get_superadmin(db) is None


def test_create_superadmin_once(db: Session) -> None:
    create_superadmin(
        db,
        email="admin@example.com",
        password="a-strong-local-password",
    )
    assert users_repo.get_superadmin(db) is not None
    with pytest.raises(SeedError, match="already exists"):
        create_superadmin(
            db,
            email="other@example.com",
            password="another-strong-password",
        )


def test_ensure_superadmin_rejects_empty_password(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(SeedError, match="empty"):
            ensure_superadmin(db)
        assert users_repo.get_superadmin(db) is None
    finally:
        get_settings.cache_clear()
        # Restore test password for later fixtures in this process.
        monkeypatch.setenv("SUPERADMIN_PASSWORD", "changeme-superadmin")
        get_settings.cache_clear()
