from datetime import UTC, datetime, timedelta
import time

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
) -> None:
    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
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


def test_history_order_is_submitted_at_descending(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="HistOrder FC",
        admin_email="historder-admin@example.com",
        coach_email="historder-coach@example.com",
    )
    questionnaire_id = _create_rating_questionnaire(client, coach_headers)
    player_headers, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="HistOrder Squad",
        player_email="historder-player@example.com",
    )

    _assign_team(
        client,
        coach_headers,
        questionnaire_id=questionnaire_id,
        team_id=team_id,
    )
    _submit_rating(client, player_headers, 2)
    time.sleep(0.05)
    _assign_team(
        client,
        coach_headers,
        questionnaire_id=questionnaire_id,
        team_id=team_id,
    )
    _submit_rating(client, player_headers, 4)

    history = client.get("/api/v1/player/history", headers=player_headers)
    assert history.status_code == 200
    submissions = history.json()["submissions"]
    assert len(submissions) == 2
    assert submissions[0]["answers"] == {"fatigue": 4}
    assert submissions[1]["answers"] == {"fatigue": 2}
    assert submissions[0]["submitted_at"] >= submissions[1]["submitted_at"]


def test_history_only_includes_caller_submissions(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="HistIso FC",
        admin_email="histiso-admin@example.com",
        coach_email="histiso-coach@example.com",
    )
    questionnaire_id = _create_rating_questionnaire(client, coach_headers)
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "HistIso Squad"},
    ).json()

    players: list[dict[str, str]] = []
    for email in ["histiso-a@example.com", "histiso-b@example.com"]:
        invite = client.post(
            f"/api/v1/teams/{team['id']}/players",
            headers=coach_headers,
            json={"name": email.split("@")[0], "email": email},
        ).json()
        accepted = client.post(
            "/api/v1/auth/accept-invite",
            json={
                "token": token_from_invite_link(invite["invite_link"]),
                "password": "playerpass1",
            },
        )
        assert accepted.status_code == 200
        players.append(
            {"Authorization": f"Bearer {accepted.json()['access_token']}"}
        )

    _assign_team(
        client,
        coach_headers,
        questionnaire_id=questionnaire_id,
        team_id=team["id"],
    )
    _submit_rating(client, players[0], 3)
    _submit_rating(client, players[1], 5)

    history_a = client.get("/api/v1/player/history", headers=players[0])
    assert history_a.status_code == 200
    body_a = history_a.json()
    assert len(body_a["submissions"]) == 1
    assert body_a["submissions"][0]["answers"] == {"fatigue": 3}
    assert all(s["answers"] != {"fatigue": 5} for s in body_a["submissions"])

    history_b = client.get("/api/v1/player/history", headers=players[1])
    assert history_b.status_code == 200
    assert len(history_b.json()["submissions"]) == 1
    assert history_b.json()["submissions"][0]["answers"] == {"fatigue": 5}


def test_rating_trends_keep_last_five_values(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="HistTrend FC",
        admin_email="histtrend-admin@example.com",
        coach_email="histtrend-coach@example.com",
    )
    questionnaire_id = _create_rating_questionnaire(client, coach_headers)
    player_headers, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="HistTrend Squad",
        player_email="histtrend-player@example.com",
    )

    values = [1, 2, 3, 4, 5, 2]
    for value in values:
        _assign_team(
            client,
            coach_headers,
            questionnaire_id=questionnaire_id,
            team_id=team_id,
        )
        _submit_rating(client, player_headers, value)

    history = client.get("/api/v1/player/history", headers=player_headers)
    assert history.status_code == 200
    trends = history.json()["rating_trends"]
    assert len(trends) == 1
    assert trends[0]["question_id"] == "fatigue"
    assert trends[0]["values"] == [2, 3, 4, 5, 2]
