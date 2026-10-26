from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.core.config import get_settings


def token_from_invite_link(invite_link: str) -> str:
    query = parse_qs(urlparse(invite_link).query)
    return query["token"][0]


def superadmin_headers(client: TestClient) -> dict[str, str]:
    settings = get_settings()
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.superadmin_email,
            "password": settings.superadmin_password,
        },
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
