from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

import uuid

from app.models import User
from app.repositories import questionnaires as questionnaires_repo
from tests.helpers import (
    bootstrap_coach,
    bootstrap_player_on_team,
    token_from_invite_link,
)


def _yes_no_questions() -> list[dict]:
    return [
        {
            "id": "ready",
            "prompt": "Ready to train?",
            "type": "yes_no",
            "required": True,
        }
    ]


def _create_questionnaire(client: TestClient, coach_headers: dict[str, str]) -> str:
    created = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={
            "name": "Daily check",
            "questions": _yes_no_questions(),
        },
    )
    assert created.status_code == 200
    return created.json()["id"]


def test_team_assignment_creates_occurrence_per_player(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(client)
    questionnaire_id = _create_questionnaire(client, coach_headers)
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "Squad"},
    ).json()

    for i, email in enumerate(["p1@example.com", "p2@example.com"]):
        invite = client.post(
            f"/api/v1/teams/{team['id']}/players",
            headers=coach_headers,
            json={"name": f"Player {i}", "email": email},
        )
        assert invite.status_code == 200

    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assigned = client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": questionnaire_id,
            "target_type": "team",
            "team_id": team["id"],
            "due_at": due,
            "channel": "in_app",
            "schedule": "once",
        },
    )
    assert assigned.status_code == 200
    assert assigned.json()["occurrence_count"] == 2


def test_missing_required_answer_returns_422_leaves_pending(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Miss FC",
        admin_email="miss-admin@example.com",
        coach_email="miss-coach@example.com",
    )
    questionnaire_id = _create_questionnaire(client, coach_headers)
    player_headers, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="Miss Team",
        player_email="miss-player@example.com",
    )
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
        },
    )
    assert assigned.status_code == 200

    occurrences = client.get(
        "/api/v1/player/occurrences", headers=player_headers
    )
    assert occurrences.status_code == 200
    assert len(occurrences.json()) == 1
    occurrence_id = occurrences.json()[0]["id"]
    assert occurrences.json()[0]["status"] == "pending"

    bad = client.post(
        f"/api/v1/player/occurrences/{occurrence_id}/responses",
        headers=player_headers,
        json={"answers": {}},
    )
    assert bad.status_code == 422

    again = client.get("/api/v1/player/occurrences", headers=player_headers)
    assert again.status_code == 200
    assert again.json()[0]["status"] == "pending"


def test_second_submit_returns_409(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Dup FC",
        admin_email="dup-admin@example.com",
        coach_email="dup-coach@example.com",
    )
    questionnaire_id = _create_questionnaire(client, coach_headers)
    player_headers, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="Dup Team",
        player_email="dup-player@example.com",
    )
    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": questionnaire_id,
            "target_type": "team",
            "team_id": team_id,
            "due_at": due,
            "channel": "in_app",
        },
    )
    occurrence_id = client.get(
        "/api/v1/player/occurrences", headers=player_headers
    ).json()[0]["id"]

    first = client.post(
        f"/api/v1/player/occurrences/{occurrence_id}/responses",
        headers=player_headers,
        json={"answers": {"ready": True}},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/player/occurrences/{occurrence_id}/responses",
        headers=player_headers,
        json={"answers": {"ready": False}},
    )
    assert second.status_code == 409


def test_player_cannot_submit_another_players_occurrence(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Other FC",
        admin_email="other-admin@example.com",
        coach_email="other-coach@example.com",
    )
    questionnaire_id = _create_questionnaire(client, coach_headers)
    player_a, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="Other Team",
        player_email="player-a@example.com",
    )
    invite_b = client.post(
        f"/api/v1/teams/{team_id}/players",
        headers=coach_headers,
        json={"name": "Player B", "email": "player-b@example.com"},
    ).json()
    accepted_b = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(invite_b["invite_link"]),
            "password": "playerpass2",
        },
    )
    player_b = {
        "Authorization": f"Bearer {accepted_b.json()['access_token']}"
    }

    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": questionnaire_id,
            "target_type": "team",
            "team_id": team_id,
            "due_at": due,
            "channel": "in_app",
        },
    )
    occurrence_a = client.get(
        "/api/v1/player/occurrences", headers=player_a
    ).json()[0]["id"]

    denied = client.post(
        f"/api/v1/player/occurrences/{occurrence_a}/responses",
        headers=player_b,
        json={"answers": {"ready": True}},
    )
    assert denied.status_code == 404


def test_channel_whatsapp_returns_422(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="WA FC",
        admin_email="wa-admin@example.com",
        coach_email="wa-coach@example.com",
    )
    questionnaire_id = _create_questionnaire(client, coach_headers)
    _, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="WA Team",
        player_email="wa-player@example.com",
    )
    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    bad = client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": questionnaire_id,
            "target_type": "team",
            "team_id": team_id,
            "due_at": due,
            "channel": "whatsapp",
        },
    )
    assert bad.status_code == 422


def test_assign_superseded_questionnaire_returns_422(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="OldQ FC",
        admin_email="oldq-admin@example.com",
        coach_email="oldq-coach@example.com",
    )
    questionnaire_id = _create_questionnaire(client, coach_headers)
    _, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="OldQ Team",
        player_email="oldq-player@example.com",
    )

    row = questionnaires_repo.get_questionnaire_by_id(db, uuid.UUID(questionnaire_id))
    assert row is not None
    row.locked_at = datetime.now(UTC)
    db.commit()

    newer = client.patch(
        f"/api/v1/questionnaires/{questionnaire_id}",
        headers=coach_headers,
        json={"name": "Daily check v2"},
    )
    assert newer.status_code == 200

    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    bad = client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": questionnaire_id,
            "target_type": "team",
            "team_id": team_id,
            "due_at": due,
            "channel": "in_app",
        },
    )
    assert bad.status_code == 422


def test_required_short_text_empty_returns_422(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Text FC",
        admin_email="text-admin@example.com",
        coach_email="text-coach@example.com",
    )
    created = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={
            "name": "Notes",
            "questions": [
                {
                    "id": "note",
                    "prompt": "Any notes?",
                    "type": "short_text",
                    "required": True,
                    "max_length": 280,
                }
            ],
        },
    )
    assert created.status_code == 200
    player_headers, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="Text Team",
        player_email="text-player@example.com",
    )
    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": created.json()["id"],
            "target_type": "team",
            "team_id": team_id,
            "due_at": due,
            "channel": "in_app",
        },
    )
    occurrence_id = client.get(
        "/api/v1/player/occurrences", headers=player_headers
    ).json()[0]["id"]
    bad = client.post(
        f"/api/v1/player/occurrences/{occurrence_id}/responses",
        headers=player_headers,
        json={"answers": {"note": "   "}},
    )
    assert bad.status_code == 422


def test_response_immutable_via_sql(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Imm FC",
        admin_email="imm-admin@example.com",
        coach_email="imm-coach@example.com",
    )
    questionnaire_id = _create_questionnaire(client, coach_headers)
    player_headers, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="Imm Team",
        player_email="imm-player@example.com",
    )
    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": questionnaire_id,
            "target_type": "team",
            "team_id": team_id,
            "due_at": due,
            "channel": "in_app",
        },
    )
    occurrence_id = client.get(
        "/api/v1/player/occurrences", headers=player_headers
    ).json()[0]["id"]
    submitted = client.post(
        f"/api/v1/player/occurrences/{occurrence_id}/responses",
        headers=player_headers,
        json={"answers": {"ready": True}},
    )
    assert submitted.status_code == 200
    response_id = submitted.json()["id"]

    try:
        db.execute(
            text(
                "UPDATE responses SET answers = '{}'::jsonb WHERE id = :id"
            ),
            {"id": response_id},
        )
        db.commit()
        assert False, "expected immutability trigger to raise"
    except Exception as exc:
        db.rollback()
        assert "immutable" in str(exc).lower()
