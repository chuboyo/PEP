from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    AssignmentTarget,
    OccurrenceStatus,
    PlayerOccurrence,
    RoutineAssignment,
    RoutineAssignmentStatus,
    User,
)
from tests.helpers import (
    bootstrap_coach,
    bootstrap_player_on_team,
    superadmin_headers,
    token_from_invite_link,
)

CRON_SECRET = "test-cron-secret"


def _bootstrap_club_with_admin(
    client: TestClient,
    *,
    club_name: str,
    admin_email: str,
) -> tuple[dict[str, str], str]:
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
    assert admin.status_code == 200
    return (
        {"Authorization": f"Bearer {admin.json()['access_token']}"},
        club["id"],
    )


def test_metrics_match_fixture_and_have_no_answers(
    client: TestClient, superadmin: User
) -> None:
    admin_headers, org_id = _bootstrap_club_with_admin(
        client,
        club_name="Metrics FC",
        admin_email="metrics-admin@example.com",
    )
    coach_invite = client.post(
        f"/api/v1/organizations/{org_id}/coaches",
        headers=admin_headers,
        json={"name": "Casey Coach", "email": "metrics-coach@example.com"},
    ).json()
    coach = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(coach_invite["invite_link"]),
            "password": "coachpass1",
        },
    )
    assert coach.status_code == 200
    coach_headers = {"Authorization": f"Bearer {coach.json()['access_token']}"}

    q = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={
            "name": "Readiness",
            "questions": [
                {
                    "id": "fatigue",
                    "prompt": "Fatigue?",
                    "type": "rating",
                    "required": True,
                    "min": 1,
                    "max": 5,
                }
            ],
        },
    )
    assert q.status_code == 200
    player_headers, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="Metrics Squad",
        player_email="metrics-player@example.com",
    )
    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assigned = client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": q.json()["id"],
            "target_type": "team",
            "team_id": team_id,
            "due_at": due,
            "channel": "in_app",
        },
    )
    assert assigned.status_code == 200
    occ = client.get("/api/v1/player/occurrences", headers=player_headers)
    assert occ.status_code == 200
    pending = [o for o in occ.json() if o["status"] == "pending"]
    assert pending
    submitted = client.post(
        f"/api/v1/player/occurrences/{pending[0]['id']}/responses",
        headers=player_headers,
        json={"answers": {"fatigue": 4}},
    )
    assert submitted.status_code == 200

    routine = client.post(
        "/api/v1/routines",
        headers=coach_headers,
        json={
            "name": "Recovery day",
            "description": "Light recovery work",
            "objective": "Reduce fatigue",
            "exercises": [
                {"name": "Light cycling", "duration_minutes": 10},
            ],
            "duration_minutes": 10,
            "intensity": "low",
            "frequency": "as needed",
            "start_date": datetime.now(UTC).date().isoformat(),
            "end_date": (datetime.now(UTC) + timedelta(days=7)).date().isoformat(),
            "instructions": "Keep heart rate easy",
            "team_id": team_id,
        },
    )
    assert routine.status_code == 200, routine.text
    player_routines = client.get("/api/v1/routines", headers=player_headers)
    assert player_routines.status_code == 200
    assignment_id = player_routines.json()[0]["id"]
    transition = client.post(
        f"/api/v1/player/routines/{assignment_id}/status",
        headers=player_headers,
        json={"status": "in_progress"},
    )
    assert transition.status_code == 200

    metrics = client.get(
        f"/api/v1/organizations/{org_id}/metrics",
        headers=admin_headers,
    )
    assert metrics.status_code == 200
    body = metrics.json()
    assert "answers" not in json.dumps(body)
    assert body["organization_id"] == org_id
    assert body["coach_count"] == 1
    assert body["player_count"] == 1
    assert body["active_player_count"] == 1
    assert body["questionnaire_completed_count"] == 1
    assert body["questionnaire_occurrence_count"] == 1
    assert body["routine_counts"] == {
        "assigned": 1,
        "in_progress": 1,
        "completed": 0,
    }

    # Superadmin can also read metrics.
    sa = client.get(
        f"/api/v1/organizations/{org_id}/metrics",
        headers=superadmin_headers(client),
    )
    assert sa.status_code == 200
    assert sa.json()["coach_count"] == 1


def test_coach_on_other_club_metrics_returns_404(
    client: TestClient, superadmin: User
) -> None:
    coach_a, org_a = bootstrap_coach(
        client,
        club_name="Club A Metrics",
        admin_email="club-a-metrics-admin@example.com",
        coach_email="club-a-metrics-coach@example.com",
    )
    _, org_b = bootstrap_coach(
        client,
        club_name="Club B Metrics",
        admin_email="club-b-metrics-admin@example.com",
        coach_email="club-b-metrics-coach@example.com",
    )
    other = client.get(
        f"/api/v1/organizations/{org_b}/metrics",
        headers=coach_a,
    )
    assert other.status_code == 404
    same = client.get(
        f"/api/v1/organizations/{org_a}/metrics",
        headers=coach_a,
    )
    assert same.status_code == 403


def test_deactivate_coach_hands_off_teams_to_remaining_coaches(
    client: TestClient, superadmin: User
) -> None:
    admin_headers, org_id = _bootstrap_club_with_admin(
        client,
        club_name="Handoff FC",
        admin_email="handoff-admin@example.com",
    )
    invite_a = client.post(
        f"/api/v1/organizations/{org_id}/coaches",
        headers=admin_headers,
        json={"name": "Coach A", "email": "handoff-coach-a@example.com"},
    ).json()
    accept_a = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(invite_a["invite_link"]),
            "password": "coachpass1",
        },
    )
    coach_a = {"Authorization": f"Bearer {accept_a.json()['access_token']}"}

    invite_b = client.post(
        f"/api/v1/organizations/{org_id}/coaches",
        headers=admin_headers,
        json={"name": "Coach B", "email": "handoff-coach-b@example.com"},
    ).json()
    accept_b = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(invite_b["invite_link"]),
            "password": "coachpass1",
        },
    )
    coach_b = {"Authorization": f"Bearer {accept_b.json()['access_token']}"}

    team = client.post(
        "/api/v1/teams",
        headers=coach_a,
        json={"name": "Handoff Squad"},
    ).json()

    before = client.get(f"/api/v1/teams/{team['id']}", headers=coach_b)
    assert before.status_code == 404

    coaches = client.get(
        f"/api/v1/organizations/{org_id}/coaches",
        headers=admin_headers,
    ).json()
    coach_a_id = next(
        c["user_id"] for c in coaches if c["email"] == "handoff-coach-a@example.com"
    )
    deact = client.post(
        f"/api/v1/organizations/{org_id}/coaches/{coach_a_id}/deactivate",
        headers=admin_headers,
    )
    assert deact.status_code == 204

    after = client.get(f"/api/v1/teams/{team['id']}", headers=coach_b)
    assert after.status_code == 200
    assert after.json()["name"] == "Handoff Squad"
    listed = client.get("/api/v1/teams", headers=coach_b)
    assert listed.status_code == 200
    assert any(t["id"] == team["id"] for t in listed.json())


def test_deactivate_accepted_coach_can_be_reinvited(
    client: TestClient, superadmin: User
) -> None:
    """Accepted then deactivated coaches must be inviteable again."""
    admin_headers, org_id = _bootstrap_club_with_admin(
        client,
        club_name="Reinvite Coach FC",
        admin_email="reinvite-coach-admin@example.com",
    )
    coach_invite = client.post(
        f"/api/v1/organizations/{org_id}/coaches",
        headers=admin_headers,
        json={"name": "Return Coach", "email": "reinvite-coach@example.com"},
    ).json()
    accepted = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(coach_invite["invite_link"]),
            "password": "coachpass1",
        },
    )
    assert accepted.status_code == 200
    old_refresh = accepted.json()["refresh_token"]
    coaches = client.get(
        f"/api/v1/organizations/{org_id}/coaches",
        headers=admin_headers,
    ).json()
    coach_user_id = coaches[0]["user_id"]

    deact = client.post(
        f"/api/v1/organizations/{org_id}/coaches/{coach_user_id}/deactivate",
        headers=admin_headers,
    )
    assert deact.status_code == 204

    reinvited = client.post(
        f"/api/v1/organizations/{org_id}/coaches",
        headers=admin_headers,
        json={"name": "Return Coach", "email": "reinvite-coach@example.com"},
    )
    assert reinvited.status_code == 200, reinvited.text
    ok = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(reinvited.json()["invite_link"]),
            "password": "coachpass2",
        },
    )
    assert ok.status_code == 200

    # Prior occupant's refresh must not mint tokens for the reclaimed account.
    stolen = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert stolen.status_code == 401


def test_deactivate_coach_blocks_login_and_stale_token(
    client: TestClient, superadmin: User
) -> None:
    admin_headers, org_id = _bootstrap_club_with_admin(
        client,
        club_name="Deact Coach FC",
        admin_email="deact-coach-admin@example.com",
    )
    coach_invite = client.post(
        f"/api/v1/organizations/{org_id}/coaches",
        headers=admin_headers,
        json={"name": "Soon Gone", "email": "deact-coach@example.com"},
    ).json()
    coach = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(coach_invite["invite_link"]),
            "password": "coachpass1",
        },
    )
    assert coach.status_code == 200
    coach_token = coach.json()["access_token"]
    coach_headers = {"Authorization": f"Bearer {coach_token}"}

    coaches = client.get(
        f"/api/v1/organizations/{org_id}/coaches",
        headers=admin_headers,
    )
    assert coaches.status_code == 200
    assert len(coaches.json()) == 1
    coach_user_id = coaches.json()[0]["user_id"]

    # Create a questionnaire so a later assign attempt is meaningful.
    q = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={
            "name": "Before deact",
            "questions": [
                {
                    "id": "q1",
                    "prompt": "Ok?",
                    "type": "yes_no",
                    "required": True,
                }
            ],
        },
    )
    assert q.status_code == 200
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "Deact Team"},
    ).json()

    deact = client.post(
        f"/api/v1/organizations/{org_id}/coaches/{coach_user_id}/deactivate",
        headers=admin_headers,
    )
    assert deact.status_code == 204

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "deact-coach@example.com", "password": "coachpass1"},
    )
    assert login.status_code == 401

    stale_assign = client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": q.json()["id"],
            "target_type": "team",
            "team_id": team["id"],
            "due_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "channel": "in_app",
        },
    )
    assert stale_assign.status_code == 403


def test_deactivate_player_clears_phone_so_old_whatsapp_cannot_bind(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    coach_headers, org_id = bootstrap_coach(
        client,
        club_name="Phone Clear FC",
        admin_email="phone-clear-admin@example.com",
        coach_email="phone-clear-coach@example.com",
    )
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "Phone Clear Team"},
    ).json()
    invite = client.post(
        f"/api/v1/teams/{team['id']}/players",
        headers=coach_headers,
        json={
            "name": "Pat Player",
            "email": "phone-clear-player@example.com",
            "phone_e164": "+15559876543",
        },
    )
    assert invite.status_code == 200
    accepted = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(invite.json()["invite_link"]),
            "password": "playerpass1",
        },
    )
    assert accepted.status_code == 200
    player_headers = {
        "Authorization": f"Bearer {accepted.json()['access_token']}"
    }
    player_id = client.get("/api/v1/me", headers=player_headers).json()["id"]

    deact = client.post(
        f"/api/v1/organizations/{org_id}/players/{player_id}/deactivate",
        headers=coach_headers,
    )
    assert deact.status_code == 204

    db.expire_all()
    user = db.get(User, player_id)
    assert user is not None
    assert user.phone_e164 is None

    # Re-invite same email without a phone — must not restore the old number.
    reinvite = client.post(
        f"/api/v1/teams/{team['id']}/players",
        headers=coach_headers,
        json={"name": "Pat Player", "email": "phone-clear-player@example.com"},
    )
    assert reinvite.status_code == 200
    db.expire_all()
    user = db.get(User, player_id)
    assert user is not None
    assert user.phone_e164 is None


def test_deactivate_player_removes_open_routines(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    coach_headers, org_id = bootstrap_coach(
        client,
        club_name="Routine Deact FC",
        admin_email="routine-deact-admin@example.com",
        coach_email="routine-deact-coach@example.com",
    )
    player_headers, team_id, player_email = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="Routine Deact Team",
        player_email="routine-deact-player@example.com",
    )
    player_id = client.get("/api/v1/me", headers=player_headers).json()["id"]
    created = client.post(
        "/api/v1/routines",
        headers=coach_headers,
        json={
            "name": "Recovery day",
            "description": "Light recovery work",
            "objective": "Reduce fatigue",
            "exercises": [{"name": "Light cycling", "duration_minutes": 10}],
            "duration_minutes": 10,
            "intensity": "low",
            "frequency": "as needed",
            "start_date": datetime.now(UTC).date().isoformat(),
            "end_date": (datetime.now(UTC) + timedelta(days=7)).date().isoformat(),
            "instructions": "Easy",
            "team_id": team_id,
        },
    )
    assert created.status_code == 200
    listed = client.get("/api/v1/routines", headers=player_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assignment_id = listed.json()[0]["id"]
    started = client.post(
        f"/api/v1/player/routines/{assignment_id}/status",
        headers=player_headers,
        json={"status": "in_progress"},
    )
    assert started.status_code == 200

    deact = client.post(
        f"/api/v1/organizations/{org_id}/players/{player_id}/deactivate",
        headers=coach_headers,
    )
    assert deact.status_code == 204

    db.expire_all()
    open_rows = list(
        db.scalars(
            select(RoutineAssignment).where(
                RoutineAssignment.player_id == player_id,
                RoutineAssignment.status.in_(
                    [
                        RoutineAssignmentStatus.NOT_STARTED,
                        RoutineAssignmentStatus.IN_PROGRESS,
                    ]
                ),
            )
        )
    )
    assert open_rows == []

    # Reinvite same email — open routines must not reappear.
    invite = client.post(
        f"/api/v1/teams/{team_id}/players",
        headers=coach_headers,
        json={"name": "Pat Player", "email": player_email},
    )
    assert invite.status_code == 200
    accepted = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(invite.json()["invite_link"]),
            "password": "playerpass2",
        },
    )
    assert accepted.status_code == 200
    new_headers = {
        "Authorization": f"Bearer {accepted.json()['access_token']}"
    }
    listed_again = client.get("/api/v1/routines", headers=new_headers)
    assert listed_again.status_code == 200
    assert listed_again.json() == []


def test_deactivate_player_closes_surveys_and_stops_recurrence(
    client: TestClient,
    superadmin: User,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CRON_SECRET", CRON_SECRET)
    get_settings.cache_clear()
    try:
        coach_headers, org_id = bootstrap_coach(
            client,
            club_name="Stop Survey FC",
            admin_email="stop-survey-admin@example.com",
            coach_email="stop-survey-coach@example.com",
        )
        q = client.post(
            "/api/v1/questionnaires",
            headers=coach_headers,
            json={
                "name": "Daily Q",
                "questions": [
                    {
                        "id": "ok",
                        "prompt": "Ok?",
                        "type": "yes_no",
                        "required": True,
                    }
                ],
            },
        )
        assert q.status_code == 200
        player_headers, team_id, _ = bootstrap_player_on_team(
            client,
            coach_headers,
            team_name="Stop Survey Team",
            player_email="stop-survey-player@example.com",
        )
        player_id = client.get("/api/v1/me", headers=player_headers).json()["id"]
        due = datetime.now(UTC) - timedelta(hours=25)
        assigned = client.post(
            "/api/v1/assignments",
            headers=coach_headers,
            json={
                "questionnaire_id": q.json()["id"],
                "target_type": "team",
                "team_id": team_id,
                "due_at": due.isoformat(),
                "channel": "in_app",
                "schedule": "daily",
                "starts_on": (due - timedelta(days=1)).date().isoformat(),
            },
        )
        assert assigned.status_code == 200
        assignment_id = assigned.json()["id"]

        deact = client.post(
            f"/api/v1/organizations/{org_id}/players/{player_id}/deactivate",
            headers=coach_headers,
        )
        assert deact.status_code == 204

        db.expire_all()
        occurrence = db.scalar(
            select(PlayerOccurrence).where(
                PlayerOccurrence.player_id == player_id
            )
        )
        assert occurrence is not None
        assert occurrence.status == OccurrenceStatus.MISSED
        targets = list(
            db.scalars(
                select(AssignmentTarget).where(
                    AssignmentTarget.assignment_id == assignment_id,
                    AssignmentTarget.user_id == player_id,
                )
            )
        )
        assert targets == []

        run = client.post(
            "/api/v1/internal/reminders",
            headers={"X-Cron-Secret": CRON_SECRET},
        )
        assert run.status_code == 200
        db.expire_all()
        occ_count = len(
            list(
                db.scalars(
                    select(PlayerOccurrence).where(
                        PlayerOccurrence.player_id == player_id
                    )
                )
            )
        )
        assert occ_count == 1
    finally:
        get_settings.cache_clear()


def test_deactivate_player_by_admin_and_sharing_coach(
    client: TestClient, superadmin: User
) -> None:
    admin_headers, org_id = _bootstrap_club_with_admin(
        client,
        club_name="Deact Player FC",
        admin_email="deact-player-admin@example.com",
    )
    coach_invite = client.post(
        f"/api/v1/organizations/{org_id}/coaches",
        headers=admin_headers,
        json={"name": "Share Coach", "email": "deact-player-coach@example.com"},
    ).json()
    coach = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(coach_invite["invite_link"]),
            "password": "coachpass1",
        },
    )
    coach_headers = {"Authorization": f"Bearer {coach.json()['access_token']}"}

    other_coach, other_org = bootstrap_coach(
        client,
        club_name="Other Deact FC",
        admin_email="other-deact-admin@example.com",
        coach_email="other-deact-coach@example.com",
    )

    player_headers, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="Deact Players",
        player_email="deact-player@example.com",
    )
    me = client.get("/api/v1/me", headers=player_headers)
    assert me.status_code == 200
    player_id = me.json()["id"]

    # Unrelated coach cannot deactivate.
    bad = client.post(
        f"/api/v1/organizations/{org_id}/players/{player_id}/deactivate",
        headers=other_coach,
    )
    assert bad.status_code == 404

    # Sharing coach can deactivate.
    by_coach = client.post(
        f"/api/v1/organizations/{org_id}/players/{player_id}/deactivate",
        headers=coach_headers,
    )
    assert by_coach.status_code == 204

    roster = client.get(f"/api/v1/teams/{team_id}", headers=coach_headers)
    assert roster.status_code == 200
    assert all(m["user_id"] != player_id for m in roster.json()["members"])

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "deact-player@example.com", "password": "playerpass1"},
    )
    assert login.status_code == 401

    # Fresh player on the same team for club-admin path.
    invite2 = client.post(
        f"/api/v1/teams/{team_id}/players",
        headers=coach_headers,
        json={"name": "Pat Two", "email": "deact-player-2@example.com"},
    )
    assert invite2.status_code == 200
    accepted2 = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(invite2.json()["invite_link"]),
            "password": "playerpass1",
        },
    )
    assert accepted2.status_code == 200
    player2_headers = {
        "Authorization": f"Bearer {accepted2.json()['access_token']}"
    }
    me2 = client.get("/api/v1/me", headers=player2_headers).json()
    by_admin = client.post(
        f"/api/v1/organizations/{org_id}/players/{me2['id']}/deactivate",
        headers=admin_headers,
    )
    assert by_admin.status_code == 204
    assert other_org  # used for isolation
