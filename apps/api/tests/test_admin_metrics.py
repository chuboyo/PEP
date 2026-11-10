from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.models import User
from tests.helpers import (
    bootstrap_coach,
    bootstrap_player_on_team,
    superadmin_headers,
    token_from_invite_link,
)


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
