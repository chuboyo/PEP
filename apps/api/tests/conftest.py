from collections.abc import Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models import (
    Membership,
    MembershipRole,
    MembershipStatus,
    Organization,
    OrganizationStatus,
    PlatformRole,
    User,
    UserStatus,
)
from app.services.seed import ensure_superadmin

settings = get_settings()
test_engine = create_engine(settings.test_database_url, pool_pre_ping=True)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def migrate_test_database() -> None:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.test_database_url)
    command.upgrade(cfg, "head")


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    with test_engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE refresh_tokens, memberships, organizations, users "
                "RESTART IDENTITY CASCADE"
            )
        )
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def superadmin(db: Session) -> User:
    ensure_superadmin(db)
    user = db.scalar(select(User).where(User.platform_role == PlatformRole.SUPERADMIN))
    assert user is not None
    return user


@pytest.fixture()
def coach_with_orgs(db: Session) -> tuple[User, Organization, Organization]:
    org_a = Organization(name="Club A", status=OrganizationStatus.ACTIVE)
    org_b = Organization(name="Club B", status=OrganizationStatus.ACTIVE)
    db.add_all([org_a, org_b])
    db.flush()

    coach = User(
        email="coach@example.com",
        name="Coach",
        password_hash=hash_password("coach-password"),
        status=UserStatus.ACTIVE,
        platform_role=None,
    )
    db.add(coach)
    db.flush()
    db.add(
        Membership(
            user_id=coach.id,
            organization_id=org_a.id,
            role=MembershipRole.COACH,
            status=MembershipStatus.ACTIVE,
        )
    )
    db.commit()
    db.refresh(coach)
    db.refresh(org_a)
    db.refresh(org_b)
    return coach, org_a, org_b
