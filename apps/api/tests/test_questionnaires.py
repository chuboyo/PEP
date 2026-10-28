import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.repositories import questionnaires as questionnaires_repo
from tests.helpers import bootstrap_coach, token_from_invite_link


def _valid_yes_no_questions() -> list[dict]:
    return [
        {
            "id": "ready",
            "prompt": "Ready to train?",
            "type": "yes_no",
            "required": True,
        }
    ]


def test_list_templates_and_create_from_daily_readiness(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(client)

    templates = client.get(
        "/api/v1/questionnaire-templates", headers=coach_headers
    )
    assert templates.status_code == 200
    keys = {t["key"] for t in templates.json()}
    assert "daily_readiness" in keys
    daily = next(t for t in templates.json() if t["key"] == "daily_readiness")

    created = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={
            "name": "Daily Readiness",
            "description": daily["description"],
            "questions": daily["questions"],
            "template_id": daily["id"],
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["name"] == "Daily Readiness"
    assert body["template_id"] == daily["id"]
    assert body["version"] == 1
    assert all(q["type"] == "rating" for q in body["questions"])

    listed = client.get("/api/v1/questionnaires", headers=coach_headers)
    assert listed.status_code == 200
    assert any(q["id"] == body["id"] for q in listed.json())


def test_create_custom_with_yes_no(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Custom Q FC",
        admin_email="custom-admin@example.com",
        coach_email="custom-coach@example.com",
    )
    created = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={
            "name": "Custom check",
            "description": "yes/no only",
            "questions": _valid_yes_no_questions(),
        },
    )
    assert created.status_code == 200
    assert created.json()["questions"][0]["type"] == "yes_no"


def test_rating_max_not_5_returns_422(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Rating FC",
        admin_email="rating-admin@example.com",
        coach_email="rating-coach@example.com",
    )
    bad = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={
            "name": "Bad rating",
            "questions": [
                {
                    "id": "sleep",
                    "prompt": "Sleep?",
                    "type": "rating",
                    "min": 1,
                    "max": 10,
                    "required": True,
                }
            ],
        },
    )
    assert bad.status_code == 422


def test_single_choice_11_options_returns_422(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Choice FC",
        admin_email="choice-admin@example.com",
        coach_email="choice-coach@example.com",
    )
    options = [
        {"id": f"opt_{i}", "label": f"Option {i}"} for i in range(11)
    ]
    bad = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={
            "name": "Too many",
            "questions": [
                {
                    "id": "pick",
                    "prompt": "Pick one",
                    "type": "single_choice",
                    "options": options,
                    "required": True,
                }
            ],
        },
    )
    assert bad.status_code == 422


def test_coach_other_club_gets_404(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_a, _ = bootstrap_coach(
        client,
        club_name="Club A Q",
        admin_email="a-admin@example.com",
        coach_email="a-coach@example.com",
    )
    created = client.post(
        "/api/v1/questionnaires",
        headers=coach_a,
        json={
            "name": "Private",
            "questions": _valid_yes_no_questions(),
        },
    )
    assert created.status_code == 200
    qid = created.json()["id"]

    coach_b, _ = bootstrap_coach(
        client,
        club_name="Club B Q",
        admin_email="b-admin@example.com",
        coach_email="b-coach@example.com",
    )
    denied = client.patch(
        f"/api/v1/questionnaires/{qid}",
        headers=coach_b,
        json={"name": "Hijacked"},
    )
    assert denied.status_code == 404


def test_player_create_returns_403(
    client: TestClient,
    superadmin: User,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Player Q FC",
        admin_email="pq-admin@example.com",
        coach_email="pq-coach@example.com",
    )
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "Squad"},
    ).json()
    invite = client.post(
        f"/api/v1/teams/{team['id']}/players",
        headers=coach_headers,
        json={"name": "Pat", "email": "q-player@example.com"},
    ).json()
    player = client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(invite["invite_link"]),
            "password": "playerpass1",
        },
    )
    player_headers = {
        "Authorization": f"Bearer {player.json()['access_token']}"
    }
    forbidden = client.post(
        "/api/v1/questionnaires",
        headers=player_headers,
        json={
            "name": "Nope",
            "questions": _valid_yes_no_questions(),
        },
    )
    assert forbidden.status_code == 403


def test_patch_locked_creates_new_version(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Lock FC",
        admin_email="lock-admin@example.com",
        coach_email="lock-coach@example.com",
    )
    created = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={
            "name": "Lock me",
            "questions": _valid_yes_no_questions(),
        },
    )
    assert created.status_code == 200
    qid = created.json()["id"]

    row = questionnaires_repo.get_questionnaire_by_id(db, uuid.UUID(qid))
    assert row is not None
    row.locked_at = datetime.now(UTC)
    db.commit()

    patched = client.patch(
        f"/api/v1/questionnaires/{qid}",
        headers=coach_headers,
        json={"name": "Lock me v2"},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["id"] != qid
    assert body["version"] == 2
    assert body["supersedes_id"] == qid
    assert body["name"] == "Lock me v2"
    assert body["locked_at"] is None

    listed = client.get("/api/v1/questionnaires", headers=coach_headers)
    assert listed.status_code == 200
    ids = {q["id"] for q in listed.json()}
    assert body["id"] in ids
    assert qid not in ids

    # Re-PATCHing the locked ancestor must not fork the lineage.
    forked = client.patch(
        f"/api/v1/questionnaires/{qid}",
        headers=coach_headers,
        json={"name": "Forked"},
    )
    assert forked.status_code == 409

    listed_again = client.get("/api/v1/questionnaires", headers=coach_headers)
    assert listed_again.status_code == 200
    assert [q["id"] for q in listed_again.json() if q["name"].startswith("Lock")] == [
        body["id"]
    ]
