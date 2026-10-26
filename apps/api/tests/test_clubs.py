from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_invite_token
from app.models import Invitation, Organization, User


def _superadmin_headers(client: TestClient) -> dict[str, str]:
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


def _token_from_invite_link(invite_link: str) -> str:
    query = parse_qs(urlparse(invite_link).query)
    return query["token"][0]


def test_superadmin_creates_club_and_second_admin_conflicts(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    headers = _superadmin_headers(client)
    created = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "name": "North FC",
            "admin_name": "Ada Admin",
            "admin_email": "ada@example.com",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["name"] == "North FC"
    assert body["admin_email"] == "ada@example.com"
    assert "invite_link" in body
    assert "/accept-invite?token=" in body["invite_link"]

    raw_token = _token_from_invite_link(body["invite_link"])
    invite = db.scalar(select(Invitation))
    assert invite is not None
    assert invite.token_hash == hash_invite_token(raw_token)
    assert raw_token not in invite.token_hash

    # Same email already invited to a club → 409 (one club per person).
    conflict = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "name": "Should Fail",
            "admin_name": "Other",
            "admin_email": "ada@example.com",
        },
    )
    assert conflict.status_code == 409

    # Superadmin is not club admin of the new club → 404 on coach invite.
    same_club = client.post(
        f"/api/v1/organizations/{body['id']}/coaches",
        headers=headers,
        json={"name": "Nope", "email": "other-admin@example.com"},
    )
    assert same_club.status_code == 404


def test_club_admin_registers_coach_flow(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    headers = _superadmin_headers(client)
    club = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "name": "South FC",
            "admin_name": "Club Admin",
            "admin_email": "clubadmin@example.com",
        },
    ).json()
    admin_token = _token_from_invite_link(club["invite_link"])

    before = client.post(
        "/api/v1/auth/login",
        json={"email": "coach@example.com", "password": "coach-password-1"},
    )
    assert before.status_code == 401

    accepted = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": admin_token, "password": "clubadmin-password"},
    )
    assert accepted.status_code == 200
    admin_headers = {"Authorization": f"Bearer {accepted.json()['access_token']}"}

    coach_invite = client.post(
        f"/api/v1/organizations/{club['id']}/coaches",
        headers=admin_headers,
        json={"name": "Casey Coach", "email": "coach@example.com"},
    )
    assert coach_invite.status_code == 200
    assert coach_invite.json()["invite_link"]
    coach_raw = _token_from_invite_link(coach_invite.json()["invite_link"])

    blocked_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coach@example.com", "password": "coachpass12"},
    )
    assert blocked_login.status_code == 401

    coach_accept = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": coach_raw, "password": "coachpass12"},
    )
    assert coach_accept.status_code == 200
    coach_headers = {"Authorization": f"Bearer {coach_accept.json()['access_token']}"}

    me = client.get("/api/v1/me", headers=coach_headers)
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "coach@example.com"
    assert any(m["role"] == "COACH" and m["status"] == "active" for m in body["memberships"])

    forbidden = client.post(
        "/api/v1/organizations",
        headers=coach_headers,
        json={
            "name": "Hacker FC",
            "admin_name": "Nope",
            "admin_email": "nope@example.com",
        },
    )
    assert forbidden.status_code == 403


def test_coach_cannot_invite_coach_on_own_or_other_club(
    client: TestClient,
    superadmin: User,
    coach_with_orgs: tuple[User, Organization, Organization],
) -> None:
    coach, org_a, org_b = coach_with_orgs
    login = client.post(
        "/api/v1/auth/login",
        json={"email": coach.email, "password": "coach-password"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    same_club = client.post(
        f"/api/v1/organizations/{org_a.id}/coaches",
        headers=headers,
        json={"name": "Other", "email": "other@example.com"},
    )
    assert same_club.status_code == 403

    other_club = client.post(
        f"/api/v1/organizations/{org_b.id}/coaches",
        headers=headers,
        json={"name": "Other", "email": "other2@example.com"},
    )
    assert other_club.status_code == 404


def test_list_organizations_superadmin_only(
    client: TestClient,
    superadmin: User,
    coach_with_orgs: tuple[User, Organization, Organization],
) -> None:
    headers = _superadmin_headers(client)
    listed = client.get("/api/v1/organizations", headers=headers)
    assert listed.status_code == 200
    assert isinstance(listed.json(), list)

    coach, _, _ = coach_with_orgs
    login = client.post(
        "/api/v1/auth/login",
        json={"email": coach.email, "password": "coach-password"},
    )
    coach_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    denied = client.get("/api/v1/organizations", headers=coach_headers)
    assert denied.status_code == 403


def test_second_club_admin_for_same_club_returns_409(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    """After accepting the first admin invite, inviting another CLUB_ADMIN conflicts."""
    import pytest
    from fastapi import HTTPException

    from app.models import MembershipRole
    from app.services import invitations as invitations_service

    headers = _superadmin_headers(client)
    club = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "name": "East FC",
            "admin_name": "First Admin",
            "admin_email": "first@example.com",
        },
    ).json()
    token = _token_from_invite_link(club["invite_link"])
    client.post(
        "/api/v1/auth/accept-invite",
        json={"token": token, "password": "firstadmin1"},
    )

    with pytest.raises(HTTPException) as exc:
        invitations_service.create_invitation_for_email(
            db,
            organization_id=club["id"],
            email="second@example.com",
            name="Second Admin",
            role=MembershipRole.CLUB_ADMIN,
            created_by=superadmin.id,
        )
    assert exc.value.status_code == 409
