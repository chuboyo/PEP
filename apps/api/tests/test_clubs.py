from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_invite_token
from app.models import Invitation, Organization, User
from tests.helpers import superadmin_headers, token_from_invite_link


def test_superadmin_creates_club_and_second_admin_conflicts(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    headers = superadmin_headers(client)
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

    raw_token = token_from_invite_link(body["invite_link"])
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
    headers = superadmin_headers(client)
    club = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "name": "South FC",
            "admin_name": "Club Admin",
            "admin_email": "clubadmin@example.com",
        },
    ).json()
    admin_token = token_from_invite_link(club["invite_link"])

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
    coach_raw = token_from_invite_link(coach_invite.json()["invite_link"])

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
    headers = superadmin_headers(client)
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


def test_deactivated_membership_can_be_reinvited(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    from app.models import Membership, MembershipStatus, UserStatus

    headers = superadmin_headers(client)
    club = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "name": "Deact FC",
            "admin_name": "Club Admin",
            "admin_email": "deact-admin@example.com",
        },
    ).json()
    admin_token = token_from_invite_link(club["invite_link"])
    accepted = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": admin_token, "password": "deactadmin1"},
    )
    admin_headers = {"Authorization": f"Bearer {accepted.json()['access_token']}"}

    invited = client.post(
        f"/api/v1/organizations/{club['id']}/coaches",
        headers=admin_headers,
        json={"name": "Temp Coach", "email": "deact-coach@example.com"},
    )
    assert invited.status_code == 200

    coach_rows = db.scalars(
        select(Membership).where(Membership.organization_id == club["id"])
    ).all()
    coach_row = next(m for m in coach_rows if m.role.value == "COACH")
    coach_row.status = MembershipStatus.DEACTIVATED
    coach_user = db.get(User, coach_row.user_id)
    assert coach_user is not None
    coach_user.status = UserStatus.DEACTIVATED
    db.commit()

    reinvited = client.post(
        f"/api/v1/organizations/{club['id']}/coaches",
        headers=admin_headers,
        json={"name": "Temp Coach", "email": "deact-coach@example.com"},
    )
    assert reinvited.status_code == 200
    token = token_from_invite_link(reinvited.json()["invite_link"])
    ok = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": token, "password": "coachpass12"},
    )
    assert ok.status_code == 200


def test_expired_invite_can_be_reissued(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.models import Invitation

    headers = superadmin_headers(client)
    club = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "name": "Reissue FC",
            "admin_name": "Club Admin",
            "admin_email": "reissue-admin@example.com",
        },
    ).json()
    admin_token = token_from_invite_link(club["invite_link"])
    accepted = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": admin_token, "password": "reissueadmin1"},
    )
    admin_headers = {"Authorization": f"Bearer {accepted.json()['access_token']}"}

    first = client.post(
        f"/api/v1/organizations/{club['id']}/coaches",
        headers=admin_headers,
        json={"name": "Casey Coach", "email": "reissue-coach@example.com"},
    )
    assert first.status_code == 200
    old_token = token_from_invite_link(first.json()["invite_link"])

    invite = db.scalar(
        select(Invitation).where(Invitation.token_hash == hash_invite_token(old_token))
    )
    assert invite is not None
    invite.expires_at = datetime.now(UTC) - timedelta(days=1)
    db.commit()

    expired = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": old_token, "password": "coachpass12"},
    )
    assert expired.status_code == 400

    reissued = client.post(
        f"/api/v1/organizations/{club['id']}/coaches",
        headers=admin_headers,
        json={"name": "Casey Coach", "email": "reissue-coach@example.com"},
    )
    assert reissued.status_code == 200
    new_token = token_from_invite_link(reissued.json()["invite_link"])
    assert new_token != old_token

    ok = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": new_token, "password": "coachpass12"},
    )
    assert ok.status_code == 200


def test_cannot_invite_superadmin_email(
    client: TestClient,
    superadmin: User,
) -> None:
    settings = get_settings()
    headers = superadmin_headers(client)
    club = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "name": "West FC",
            "admin_name": "Club Admin",
            "admin_email": "west-admin@example.com",
        },
    ).json()
    admin_token = token_from_invite_link(club["invite_link"])
    accepted = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": admin_token, "password": "westadmin1"},
    )
    admin_headers = {"Authorization": f"Bearer {accepted.json()['access_token']}"}

    takeover = client.post(
        f"/api/v1/organizations/{club['id']}/coaches",
        headers=admin_headers,
        json={"name": "Nope", "email": settings.superadmin_email},
    )
    assert takeover.status_code == 409

    # Superadmin password and role must remain intact.
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.superadmin_email,
            "password": settings.superadmin_password,
        },
    )
    assert login.status_code == 200
    me = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["platform_role"] == "SUPERADMIN"


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

    headers = superadmin_headers(client)
    club = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "name": "East FC",
            "admin_name": "First Admin",
            "admin_email": "first@example.com",
        },
    ).json()
    token = token_from_invite_link(club["invite_link"])
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
