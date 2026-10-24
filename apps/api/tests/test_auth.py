from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.models import Organization, User


def test_login_success(client: TestClient, superadmin: User) -> None:
    settings = get_settings()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": settings.superadmin_email, "password": settings.superadmin_password},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_wrong_password(client: TestClient, superadmin: User) -> None:
    settings = get_settings()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": settings.superadmin_email, "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_refresh_rotation_rejects_old_token(client: TestClient, superadmin: User) -> None:
    settings = get_settings()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": settings.superadmin_email, "password": settings.superadmin_password},
    )
    assert login.status_code == 200
    first_refresh = login.json()["refresh_token"]

    rotated = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != first_refresh

    reused = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert reused.status_code == 401


def test_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/me")
    assert response.status_code == 401


def test_me_with_token(client: TestClient, superadmin: User) -> None:
    settings = get_settings()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": settings.superadmin_email, "password": settings.superadmin_password},
    )
    token = login.json()["access_token"]
    response = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == settings.superadmin_email
    assert body["platform_role"] == "SUPERADMIN"
    assert body["name"] == "Superadmin"


def test_cross_club_organization_returns_404(
    client: TestClient,
    coach_with_orgs: tuple[User, Organization, Organization],
) -> None:
    coach, org_a, org_b = coach_with_orgs
    login = client.post(
        "/api/v1/auth/login",
        json={"email": coach.email, "password": "coach-password"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    allowed = client.get(f"/api/v1/organizations/{org_a.id}", headers=headers)
    assert allowed.status_code == 200
    assert allowed.json()["name"] == "Club A"

    denied = client.get(f"/api/v1/organizations/{org_b.id}", headers=headers)
    assert denied.status_code == 404
