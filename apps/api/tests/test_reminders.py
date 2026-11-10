from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    Delivery,
    DeliveryKind,
    OccurrenceStatus,
    PlayerOccurrence,
    User,
)
from app.ports.whatsapp import InMemoryWhatsApp, set_whatsapp_port
from tests.helpers import (
    bootstrap_coach,
    bootstrap_player_on_team,
    token_from_invite_link,
)

CRON_SECRET = "test-cron-secret"


@pytest.fixture()
def wa_memory() -> InMemoryWhatsApp:
    port = InMemoryWhatsApp()
    set_whatsapp_port(port)
    yield port
    set_whatsapp_port(None)


@pytest.fixture(autouse=True)
def cron_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRON_SECRET", CRON_SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _yes_no_q() -> list[dict]:
    return [
        {
            "id": "ready",
            "prompt": "Ready?",
            "type": "yes_no",
            "required": True,
        }
    ]


def _bootstrap_wa_team(
    client: TestClient,
    *,
    suffix: str,
    phone: str = "+15551112222",
) -> tuple[dict[str, str], str, str]:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name=f"Remind {suffix}",
        admin_email=f"remind-admin-{suffix}@example.com",
        coach_email=f"remind-coach-{suffix}@example.com",
    )
    created = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={"name": f"Q {suffix}", "questions": _yes_no_q()},
    )
    assert created.status_code == 200
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": f"Team {suffix}"},
    ).json()
    invite = client.post(
        f"/api/v1/teams/{team['id']}/players",
        headers=coach_headers,
        json={
            "name": "Pat Player",
            "email": f"remind-player-{suffix}@example.com",
            "phone_e164": phone,
        },
    )
    assert invite.status_code == 200
    client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(invite.json()["invite_link"]),
            "password": "playerpass1",
        },
    )
    return coach_headers, team["id"], created.json()["id"]


def _assign_whatsapp(
    client: TestClient,
    coach_headers: dict[str, str],
    *,
    questionnaire_id: str,
    team_id: str,
    due_at: datetime,
    schedule: str = "once",
    starts_on: str | None = None,
    ends_on: str | None = None,
) -> dict:
    body: dict = {
        "questionnaire_id": questionnaire_id,
        "target_type": "team",
        "team_id": team_id,
        "due_at": due_at.isoformat(),
        "channel": "whatsapp",
        "schedule": schedule,
    }
    if starts_on is not None:
        body["starts_on"] = starts_on
    if ends_on is not None:
        body["ends_on"] = ends_on
    assigned = client.post(
        "/api/v1/assignments", headers=coach_headers, json=body
    )
    assert assigned.status_code == 200, assigned.text
    return assigned.json()


def test_cron_auth_rejects_missing_and_bad_secret(
    client: TestClient, superadmin: User, wa_memory: InMemoryWhatsApp
) -> None:
    missing = client.post("/api/v1/internal/reminders")
    assert missing.status_code == 401
    bad = client.post(
        "/api/v1/internal/reminders",
        headers={"X-Cron-Secret": "wrong"},
    )
    assert bad.status_code == 401


def test_two_job_runs_create_one_reminder_delivery(
    client: TestClient,
    superadmin: User,
    db: Session,
    wa_memory: InMemoryWhatsApp,
) -> None:
    coach_headers, team_id, qid = _bootstrap_wa_team(client, suffix="idem")
    due = datetime.now(UTC) - timedelta(hours=2)
    _assign_whatsapp(
        client,
        coach_headers,
        questionnaire_id=qid,
        team_id=team_id,
        due_at=due,
    )
    wa_memory.clear()

    headers = {"X-Cron-Secret": CRON_SECRET}
    first = client.post("/api/v1/internal/reminders", headers=headers)
    assert first.status_code == 200
    assert first.json()["reminded_count"] == 1
    second = client.post("/api/v1/internal/reminders", headers=headers)
    assert second.status_code == 200
    assert second.json()["reminded_count"] == 0

    db.expire_all()
    reminders = list(
        db.scalars(
            select(Delivery).where(Delivery.kind == DeliveryKind.REMINDER)
        )
    )
    assert len(reminders) == 1
    assert any(m.kind == "template" for m in wa_memory.sent)


def test_coach_remind_second_call_returns_409(
    client: TestClient,
    superadmin: User,
    db: Session,
    wa_memory: InMemoryWhatsApp,
) -> None:
    coach_headers, team_id, qid = _bootstrap_wa_team(client, suffix="coach409")
    due = datetime.now(UTC) - timedelta(hours=1)
    _assign_whatsapp(
        client,
        coach_headers,
        questionnaire_id=qid,
        team_id=team_id,
        due_at=due,
    )
    occurrence = db.scalar(select(PlayerOccurrence).limit(1))
    assert occurrence is not None

    first = client.post(
        f"/api/v1/occurrences/{occurrence.id}/remind",
        headers=coach_headers,
    )
    assert first.status_code == 204
    second = client.post(
        f"/api/v1/occurrences/{occurrence.id}/remind",
        headers=coach_headers,
    )
    assert second.status_code == 409


def test_old_pending_becomes_missed(
    client: TestClient,
    superadmin: User,
    db: Session,
    wa_memory: InMemoryWhatsApp,
) -> None:
    coach_headers, team_id, qid = _bootstrap_wa_team(client, suffix="missed")
    due = datetime.now(UTC) - timedelta(hours=25)
    _assign_whatsapp(
        client,
        coach_headers,
        questionnaire_id=qid,
        team_id=team_id,
        due_at=due,
    )
    occurrence = db.scalar(select(PlayerOccurrence).limit(1))
    assert occurrence is not None
    oid = occurrence.id

    run = client.post(
        "/api/v1/internal/reminders",
        headers={"X-Cron-Secret": CRON_SECRET},
    )
    assert run.status_code == 200
    assert run.json()["missed_count"] == 1

    db.expire_all()
    occurrence = db.get(PlayerOccurrence, oid)
    assert occurrence is not None
    assert occurrence.status == OccurrenceStatus.MISSED


def test_in_app_remind_returns_422(
    client: TestClient, superadmin: User, wa_memory: InMemoryWhatsApp
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="InApp Remind FC",
        admin_email="inapp-remind-admin@example.com",
        coach_email="inapp-remind-coach@example.com",
    )
    created = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={"name": "InApp", "questions": _yes_no_q()},
    )
    assert created.status_code == 200
    _, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="InApp Team",
        player_email="inapp-remind-player@example.com",
    )
    due = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    assigned = client.post(
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
    assert assigned.status_code == 200
    dash = client.get(
        f"/api/v1/teams/{team_id}/dashboard",
        headers=coach_headers,
    )
    assert dash.status_code == 200
    occ_id = dash.json()["players"][0]["occurrence_id"]
    bad = client.post(
        f"/api/v1/occurrences/{occ_id}/remind",
        headers=coach_headers,
    )
    assert bad.status_code == 422


def test_daily_spawns_next_occurrence_after_window_and_respects_ends_on(
    client: TestClient,
    superadmin: User,
    db: Session,
    wa_memory: InMemoryWhatsApp,
) -> None:
    coach_headers, team_id, qid = _bootstrap_wa_team(client, suffix="daily")
    due = datetime.now(UTC) - timedelta(hours=25)
    starts = (due - timedelta(days=1)).date().isoformat()
    ends = due.date().isoformat()  # next due would be after ends_on
    _assign_whatsapp(
        client,
        coach_headers,
        questionnaire_id=qid,
        team_id=team_id,
        due_at=due,
        schedule="daily",
        starts_on=starts,
        ends_on=ends,
    )

    run = client.post(
        "/api/v1/internal/reminders",
        headers={"X-Cron-Secret": CRON_SECRET},
    )
    assert run.status_code == 200
    # Window closed + next due date after ends_on → no spawn
    assert run.json()["spawned_count"] == 0
    assert db.scalar(select(PlayerOccurrence)) is not None
    assert (
        len(list(db.scalars(select(PlayerOccurrence)))) == 1
    )

    # Without ends_on, next occurrence is created.
    coach_headers2, team_id2, qid2 = _bootstrap_wa_team(
        client, suffix="daily2", phone="+15553334444"
    )
    due2 = datetime.now(UTC) - timedelta(hours=25)
    _assign_whatsapp(
        client,
        coach_headers2,
        questionnaire_id=qid2,
        team_id=team_id2,
        due_at=due2,
        schedule="daily",
        starts_on=(due2 - timedelta(days=1)).date().isoformat(),
    )
    run2 = client.post(
        "/api/v1/internal/reminders",
        headers={"X-Cron-Secret": CRON_SECRET},
    )
    assert run2.status_code == 200
    assert run2.json()["spawned_count"] >= 1
    db.expire_all()
    # Original missed + new pending for daily2 player
    rows = list(
        db.scalars(
            select(PlayerOccurrence).where(
                PlayerOccurrence.due_at.is_not(None)
            )
        )
    )
    assert any(r.status == OccurrenceStatus.MISSED for r in rows)
    assert any(
        r.status == OccurrenceStatus.PENDING
        and r.due_at is not None
        and r.due_at > due2
        for r in rows
    )
