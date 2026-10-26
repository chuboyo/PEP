from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, User
from tests.helpers import superadmin_headers, token_from_invite_link


def _bootstrap_coach(client: TestClient, superadmin: User) -> tuple[dict[str, str], str]:
    """Create club + coach; return coach headers and organization id."""
    headers = superadmin_headers(client)
    club = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "name": "Teams FC",
            "admin_name": "Club Admin",
            "admin_email": "teams-admin@example.com",
        },
    ).json()
    admin_token = token_from_invite_link(club["invite_link"])
    admin = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": admin_token, "password": "clubadmin1"},
    )
    admin_headers = {"Authorization": f"Bearer {admin.json()['access_token']}"}

    coach_invite = client.post(
        f"/api/v1/organizations/{club['id']}/coaches",
        headers=admin_headers,
        json={"name": "Casey Coach", "email": "teams-coach@example.com"},
    ).json()
    coach_token = token_from_invite_link(coach_invite["invite_link"])
    coach = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": coach_token, "password": "coachpass1"},
    )
    return (
        {"Authorization": f"Bearer {coach.json()['access_token']}"},
        club["id"],
    )


def test_coach_creates_team_registers_player_and_player_accepts(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    coach_headers, _org_id = _bootstrap_coach(client, superadmin)

    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "U18"},
    )
    assert team.status_code == 200
    team_id = team.json()["id"]

    listed = client.get("/api/v1/teams", headers=coach_headers)
    assert listed.status_code == 200
    assert any(t["id"] == team_id for t in listed.json())

    player = client.post(
        f"/api/v1/teams/{team_id}/players",
        headers=coach_headers,
        json={
            "name": "Pat Player",
            "email": "player@example.com",
            "phone_e164": "+15551234567",
        },
    )
    assert player.status_code == 200
    assert "invite_link" in player.json()
    raw = token_from_invite_link(player.json()["invite_link"])

    accepted = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": raw, "password": "playerpass1"},
    )
    assert accepted.status_code == 200
    player_headers = {"Authorization": f"Bearer {accepted.json()['access_token']}"}

    me = client.get("/api/v1/me", headers=player_headers)
    assert me.status_code == 200
    body = me.json()
    assert any(m["role"] == "PLAYER" and m["status"] == "active" for m in body["memberships"])

    detail = client.get(f"/api/v1/teams/{team_id}", headers=coach_headers)
    assert detail.status_code == 200
    emails = {m["email"] for m in detail.json()["members"]}
    assert "player@example.com" in emails
    assert "teams-coach@example.com" in emails

    from app.models import User as UserModel

    stored = db.scalar(select(UserModel).where(UserModel.email == "player@example.com"))
    assert stored is not None
    assert stored.phone_e164 == "+15551234567"


def test_coach_not_on_team_gets_404(
    client: TestClient,
    superadmin: User,
    coach_with_orgs: tuple[User, Organization, Organization],
) -> None:
    coach_headers, _ = _bootstrap_coach(client, superadmin)
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "Private"},
    ).json()

    other_coach, _, _ = coach_with_orgs
    login = client.post(
        "/api/v1/auth/login",
        json={"email": other_coach.email, "password": "coach-password"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    denied = client.get(f"/api/v1/teams/{team['id']}", headers=other_headers)
    assert denied.status_code == 404

    denied_players = client.post(
        f"/api/v1/teams/{team['id']}/players",
        headers=other_headers,
        json={"name": "X", "email": "x@example.com"},
    )
    assert denied_players.status_code == 404


def test_player_cannot_create_team(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = _bootstrap_coach(client, superadmin)
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "Squad"},
    ).json()
    invite = client.post(
        f"/api/v1/teams/{team['id']}/players",
        headers=coach_headers,
        json={"name": "Pat", "email": "nopower@example.com"},
    ).json()
    accepted = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(invite["invite_link"]),
            "password": "playerpass1",
        },
    )
    player_headers = {"Authorization": f"Bearer {accepted.json()['access_token']}"}

    forbidden = client.post(
        "/api/v1/teams",
        headers=player_headers,
        json={"name": "Hacker Team"},
    )
    assert forbidden.status_code == 403


def test_register_player_twice_returns_409(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = _bootstrap_coach(client, superadmin)
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "Dup"},
    ).json()
    first = client.post(
        f"/api/v1/teams/{team['id']}/players",
        headers=coach_headers,
        json={"name": "Pat", "email": "dup@example.com"},
    )
    assert first.status_code == 200
    # Accept so user has credentials → second invite conflicts.
    client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(first.json()["invite_link"]),
            "password": "playerpass1",
        },
    )
    second = client.post(
        f"/api/v1/teams/{team['id']}/players",
        headers=coach_headers,
        json={"name": "Pat", "email": "dup@example.com"},
    )
    assert second.status_code == 409


def test_invalid_phone_returns_422(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = _bootstrap_coach(client, superadmin)
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "Phone"},
    ).json()
    bad = client.post(
        f"/api/v1/teams/{team['id']}/players",
        headers=coach_headers,
        json={
            "name": "Pat",
            "email": "phone@example.com",
            "phone_e164": "555-1234",
        },
    )
    assert bad.status_code == 422
