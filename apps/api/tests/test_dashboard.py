from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.models import User
from tests.helpers import (
    bootstrap_coach,
    bootstrap_player_on_team,
    token_from_invite_link,
)


def _rating_questions() -> list[dict]:
    return [
        {
            "id": "fatigue",
            "prompt": "How fatigued?",
            "type": "rating",
            "required": True,
            "min": 1,
            "max": 5,
        }
    ]


def _create_rating_questionnaire(
    client: TestClient, coach_headers: dict[str, str], name: str = "Wellness"
) -> str:
    created = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={"name": name, "questions": _rating_questions()},
    )
    assert created.status_code == 200
    return created.json()["id"]


def _assign_team(
    client: TestClient,
    coach_headers: dict[str, str],
    *,
    questionnaire_id: str,
    team_id: str,
    due_at: datetime | None = None,
) -> None:
    due = (due_at or (datetime.now(UTC) + timedelta(days=1))).isoformat()
    assigned = client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": questionnaire_id,
            "target_type": "team",
            "team_id": team_id,
            "due_at": due,
            "channel": "in_app",
            "schedule": "once",
        },
    )
    assert assigned.status_code == 200


def _submit_rating(
    client: TestClient, player_headers: dict[str, str], value: int
) -> None:
    occurrences = client.get(
        "/api/v1/player/occurrences", headers=player_headers
    )
    assert occurrences.status_code == 200
    pending = [o for o in occurrences.json() if o["status"] == "pending"]
    assert pending
    submitted = client.post(
        f"/api/v1/player/occurrences/{pending[0]['id']}/responses",
        headers=player_headers,
        json={"answers": {"fatigue": value}},
    )
    assert submitted.status_code == 200


def test_dashboard_averages_match_three_responses(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Avg FC",
        admin_email="avg-admin@example.com",
        coach_email="avg-coach@example.com",
    )
    questionnaire_id = _create_rating_questionnaire(client, coach_headers)
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "Avg Squad"},
    ).json()

    player_headers_list: list[dict[str, str]] = []
    for i, email in enumerate(
        ["avg-p1@example.com", "avg-p2@example.com", "avg-p3@example.com"]
    ):
        invite = client.post(
            f"/api/v1/teams/{team['id']}/players",
            headers=coach_headers,
            json={"name": f"Player {i}", "email": email},
        ).json()
        accepted = client.post(
            "/api/v1/auth/accept-invite",
            json={
                "token": token_from_invite_link(invite["invite_link"]),
                "password": "playerpass1",
            },
        )
        assert accepted.status_code == 200
        player_headers_list.append(
            {"Authorization": f"Bearer {accepted.json()['access_token']}"}
        )

    _assign_team(
        client,
        coach_headers,
        questionnaire_id=questionnaire_id,
        team_id=team["id"],
    )
    for headers, value in zip(
        player_headers_list, [2, 4, 5], strict=True
    ):
        _submit_rating(client, headers, value)

    dashboard = client.get(
        f"/api/v1/teams/{team['id']}/dashboard",
        headers=coach_headers,
    )
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["completion_count"] == 3
    assert body["roster_size"] == 3
    assert len(body["question_stats"]) == 1
    assert body["question_stats"][0]["question_id"] == "fatigue"
    assert body["question_stats"][0]["average"] == pytest.approx(11 / 3)
    assert len(body["players"]) == 3
    assert all(
        p["status"] == "completed" and p["answers"] is not None
        for p in body["players"]
    )


def test_two_consecutive_high_ratings_produce_one_flag(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Flag FC",
        admin_email="flag-admin@example.com",
        coach_email="flag-coach@example.com",
    )
    questionnaire_id = _create_rating_questionnaire(client, coach_headers)
    player_headers, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="Flag Squad",
        player_email="flag-player@example.com",
    )

    _assign_team(
        client,
        coach_headers,
        questionnaire_id=questionnaire_id,
        team_id=team_id,
    )
    _submit_rating(client, player_headers, 4)

    _assign_team(
        client,
        coach_headers,
        questionnaire_id=questionnaire_id,
        team_id=team_id,
    )
    _submit_rating(client, player_headers, 5)

    dashboard = client.get(
        f"/api/v1/teams/{team_id}/dashboard",
        headers=coach_headers,
    )
    assert dashboard.status_code == 200
    flags = dashboard.json()["flags"]
    high = [f for f in flags if f["type"] == "high_rating_streak"]
    assert len(high) == 1
    assert high[0]["question_id"] == "fatigue"
    assert high[0]["player_name"] == "Pat Player"


def test_coach_off_team_gets_404_on_dashboard(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_a, org_id = bootstrap_coach(
        client,
        club_name="Off FC",
        admin_email="off-admin@example.com",
        coach_email="off-coach-a@example.com",
    )
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "off-admin@example.com", "password": "clubadmin1"},
    )
    admin_headers = {
        "Authorization": f"Bearer {admin_login.json()['access_token']}"
    }
    coach_b_invite = client.post(
        f"/api/v1/organizations/{org_id}/coaches",
        headers=admin_headers,
        json={"name": "Other Coach", "email": "off-coach-b@example.com"},
    ).json()
    coach_b = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(coach_b_invite["invite_link"]),
            "password": "coachpass2",
        },
    )
    coach_b_headers = {
        "Authorization": f"Bearer {coach_b.json()['access_token']}"
    }

    _, team_id, _ = bootstrap_player_on_team(
        client,
        coach_a,
        team_name="Coach A Only",
        player_email="off-player@example.com",
    )

    denied = client.get(
        f"/api/v1/teams/{team_id}/dashboard",
        headers=coach_b_headers,
    )
    assert denied.status_code == 404


def test_club_admin_gets_404_on_player_detail(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="AdminDeny FC",
        admin_email="admindeny-admin@example.com",
        coach_email="admindeny-coach@example.com",
    )
    player_headers, _, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="AdminDeny Squad",
        player_email="admindeny-player@example.com",
    )
    player_id = client.get("/api/v1/me", headers=player_headers).json()["id"]

    admin_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admindeny-admin@example.com",
            "password": "clubadmin1",
        },
    )
    assert admin_login.status_code == 200
    admin_headers = {
        "Authorization": f"Bearer {admin_login.json()['access_token']}"
    }

    denied = client.get(
        f"/api/v1/players/{player_id}",
        headers=admin_headers,
    )
    assert denied.status_code == 404


def test_future_assignments_do_not_produce_missed_streak(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="FutureMiss FC",
        admin_email="futuremiss-admin@example.com",
        coach_email="futuremiss-coach@example.com",
    )
    questionnaire_id = _create_rating_questionnaire(client, coach_headers)
    _, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="FutureMiss Squad",
        player_email="futuremiss-player@example.com",
    )
    _assign_team(
        client,
        coach_headers,
        questionnaire_id=questionnaire_id,
        team_id=team_id,
        due_at=datetime.now(UTC) + timedelta(days=2),
    )
    _assign_team(
        client,
        coach_headers,
        questionnaire_id=questionnaire_id,
        team_id=team_id,
        due_at=datetime.now(UTC) + timedelta(days=3),
    )

    dashboard = client.get(
        f"/api/v1/teams/{team_id}/dashboard",
        headers=coach_headers,
    )
    assert dashboard.status_code == 200
    missed = [
        f for f in dashboard.json()["flags"] if f["type"] == "missed_streak"
    ]
    assert missed == []


def test_two_past_due_without_response_produce_missed_streak(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="PastMiss FC",
        admin_email="pastmiss-admin@example.com",
        coach_email="pastmiss-coach@example.com",
    )
    questionnaire_id = _create_rating_questionnaire(client, coach_headers)
    _, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="PastMiss Squad",
        player_email="pastmiss-player@example.com",
    )
    _assign_team(
        client,
        coach_headers,
        questionnaire_id=questionnaire_id,
        team_id=team_id,
        due_at=datetime.now(UTC) - timedelta(days=3),
    )
    _assign_team(
        client,
        coach_headers,
        questionnaire_id=questionnaire_id,
        team_id=team_id,
        due_at=datetime.now(UTC) - timedelta(days=1),
    )

    dashboard = client.get(
        f"/api/v1/teams/{team_id}/dashboard",
        headers=coach_headers,
    )
    assert dashboard.status_code == 200
    missed = [
        f for f in dashboard.json()["flags"] if f["type"] == "missed_streak"
    ]
    assert len(missed) == 1
    assert missed[0]["player_name"] == "Pat Player"


def test_dashboard_shows_submitted_player_answers(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Done FC",
        admin_email="done-admin@example.com",
        coach_email="done-coach@example.com",
    )
    questionnaire_id = _create_rating_questionnaire(client, coach_headers)
    player_headers, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="Done Squad",
        player_email="done-player@example.com",
    )
    _assign_team(
        client,
        coach_headers,
        questionnaire_id=questionnaire_id,
        team_id=team_id,
    )
    _submit_rating(client, player_headers, 3)

    dashboard = client.get(
        f"/api/v1/teams/{team_id}/dashboard",
        headers=coach_headers,
    )
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["completion_count"] == 1
    assert body["roster_size"] == 1
    assert body["players"][0]["answers"] == {"fatigue": 3}
    assert body["players"][0]["channel"] == "in_app"

    player_id = body["players"][0]["player_id"]
    detail = client.get(
        f"/api/v1/players/{player_id}",
        headers=coach_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["name"] == "Pat Player"
    assert len(detail.json()["occurrences"]) == 1
    assert detail.json()["occurrences"][0]["answers"] == {"fatigue": 3}
