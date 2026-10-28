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


def bootstrap_coach(
    client: TestClient,
    *,
    club_name: str = "Assign FC",
    admin_email: str = "assign-admin@example.com",
    coach_email: str = "assign-coach@example.com",
) -> tuple[dict[str, str], str]:
    """Create club + coach; return coach headers and organization id."""
    headers = superadmin_headers(client)
    club = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "name": club_name,
            "admin_name": "Club Admin",
            "admin_email": admin_email,
        },
    ).json()
    admin = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(club["invite_link"]),
            "password": "clubadmin1",
        },
    )
    admin_headers = {"Authorization": f"Bearer {admin.json()['access_token']}"}
    coach_invite = client.post(
        f"/api/v1/organizations/{club['id']}/coaches",
        headers=admin_headers,
        json={"name": "Casey Coach", "email": coach_email},
    ).json()
    coach = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(coach_invite["invite_link"]),
            "password": "coachpass1",
        },
    )
    return (
        {"Authorization": f"Bearer {coach.json()['access_token']}"},
        club["id"],
    )


def bootstrap_player_on_team(
    client: TestClient,
    coach_headers: dict[str, str],
    *,
    team_name: str = "U18",
    player_name: str = "Pat Player",
    player_email: str = "assign-player@example.com",
    password: str = "playerpass1",
) -> tuple[dict[str, str], str, str]:
    """Create team, invite+accept player. Return player headers, team id, player email."""
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": team_name},
    ).json()
    invite = client.post(
        f"/api/v1/teams/{team['id']}/players",
        headers=coach_headers,
        json={"name": player_name, "email": player_email},
    ).json()
    accepted = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(invite["invite_link"]),
            "password": password,
        },
    )
    assert accepted.status_code == 200
    return (
        {"Authorization": f"Bearer {accepted.json()['access_token']}"},
        team["id"],
        player_email,
    )
