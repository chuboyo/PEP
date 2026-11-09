from __future__ import annotations

import hashlib
import hmac
import json
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
    Response,
    User,
)
from app.ports.whatsapp import InMemoryWhatsApp, set_whatsapp_port
from app.services.whatsapp_survey import reply_id
from tests.helpers import (
    bootstrap_coach,
    bootstrap_player_on_team,
    token_from_invite_link,
)

APP_SECRET = "test-whatsapp-app-secret"
VERIFY_TOKEN = "test-verify-token"


@pytest.fixture()
def wa_memory() -> InMemoryWhatsApp:
    port = InMemoryWhatsApp()
    set_whatsapp_port(port)
    yield port
    set_whatsapp_port(None)


@pytest.fixture(autouse=True)
def whatsapp_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHATSAPP_APP_SECRET", APP_SECRET)
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", VERIFY_TOKEN)
    monkeypatch.setenv("WHATSAPP_TOKEN", "")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _sign(body: bytes) -> str:
    digest = hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _post_webhook(client: TestClient, payload: dict) -> object:
    raw = json.dumps(payload).encode("utf-8")
    return client.post(
        "/api/v1/webhooks/whatsapp",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": _sign(raw),
        },
    )


def _message_envelope(message: dict) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [message],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def _three_question_payload() -> list[dict]:
    return [
        {
            "id": "ready",
            "prompt": "Ready to train?",
            "type": "yes_no",
            "required": True,
        },
        {
            "id": "energy",
            "prompt": "Energy level",
            "type": "rating",
            "required": True,
            "min": 1,
            "max": 5,
        },
        {
            "id": "focus",
            "prompt": "Focus area",
            "type": "single_choice",
            "required": True,
            "options": [
                {"id": "speed", "label": "Speed"},
                {"id": "strength", "label": "Strength"},
            ],
        },
    ]


def _bootstrap_wa_assignment(
    client: TestClient,
    *,
    phone: str = "+15551234567",
    questions: list[dict] | None = None,
    club_suffix: str = "wa",
) -> tuple[dict[str, str], str, str, str]:
    """Return coach_headers, team_id, player_email, questionnaire_id."""
    coach_headers, _ = bootstrap_coach(
        client,
        club_name=f"Club {club_suffix}",
        admin_email=f"admin-{club_suffix}@example.com",
        coach_email=f"coach-{club_suffix}@example.com",
    )
    created = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={
            "name": "WA Check",
            "questions": questions or _three_question_payload(),
        },
    )
    assert created.status_code == 200
    questionnaire_id = created.json()["id"]

    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": f"Team {club_suffix}"},
    ).json()
    player_email = f"player-{club_suffix}@example.com"
    invite = client.post(
        f"/api/v1/teams/{team['id']}/players",
        headers=coach_headers,
        json={
            "name": "Pat Player",
            "email": player_email,
            "phone_e164": phone,
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

    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assigned = client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": questionnaire_id,
            "target_type": "team",
            "team_id": team["id"],
            "due_at": due,
            "channel": "whatsapp",
            "schedule": "once",
        },
    )
    assert assigned.status_code == 200, assigned.text
    return coach_headers, team["id"], player_email, questionnaire_id


def test_webhook_verify_challenge(client: TestClient, superadmin: User) -> None:
    ok = client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "12345",
        },
    )
    assert ok.status_code == 200
    assert ok.text == "12345"

    bad = client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "12345",
        },
    )
    assert bad.status_code == 403


def test_bad_signature_returns_401(
    client: TestClient, superadmin: User, wa_memory: InMemoryWhatsApp
) -> None:
    raw = b'{"object":"whatsapp_business_account","entry":[]}'
    response = client.post(
        "/api/v1/webhooks/whatsapp",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=deadbeef",
        },
    )
    assert response.status_code == 401


def test_short_text_whatsapp_assign_returns_422(
    client: TestClient, superadmin: User, wa_memory: InMemoryWhatsApp
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="Short FC",
        admin_email="short-admin@example.com",
        coach_email="short-coach@example.com",
    )
    created = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={
            "name": "Notes",
            "questions": [
                {
                    "id": "note",
                    "prompt": "Notes?",
                    "type": "short_text",
                    "required": True,
                    "max_length": 100,
                }
            ],
        },
    )
    assert created.status_code == 200
    team = client.post(
        "/api/v1/teams",
        headers=coach_headers,
        json={"name": "Phoned Short"},
    ).json()
    only = client.post(
        f"/api/v1/teams/{team['id']}/players",
        headers=coach_headers,
        json={
            "name": "Phoned",
            "email": "phoned-short@example.com",
            "phone_e164": "+15550002222",
        },
    )
    assert only.status_code == 200
    client.post(
        "/api/v1/auth/accept-invite",
        json={
            "token": token_from_invite_link(only.json()["invite_link"]),
            "password": "playerpass1",
        },
    )
    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    bad = client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": created.json()["id"],
            "target_type": "team",
            "team_id": team["id"],
            "due_at": due,
            "channel": "whatsapp",
        },
    )
    assert bad.status_code == 422
    assert "short_text" in bad.json()["detail"]


def test_missing_phone_whatsapp_assign_returns_422(
    client: TestClient, superadmin: User, wa_memory: InMemoryWhatsApp
) -> None:
    coach_headers, _ = bootstrap_coach(
        client,
        club_name="NoPhone FC",
        admin_email="nophone-admin@example.com",
        coach_email="nophone-coach@example.com",
    )
    created = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={"name": "Ready", "questions": _three_question_payload()[:1]},
    )
    assert created.status_code == 200
    _, team_id, _ = bootstrap_player_on_team(
        client,
        coach_headers,
        team_name="NoPhone Team",
        player_email="nophone-player@example.com",
    )
    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    bad = client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": created.json()["id"],
            "target_type": "team",
            "team_id": team_id,
            "due_at": due,
            "channel": "whatsapp",
        },
    )
    assert bad.status_code == 422
    assert "phone_e164" in bad.json()["detail"]


def test_start_moves_pending_to_in_progress_and_sends_first_question(
    client: TestClient,
    superadmin: User,
    db: Session,
    wa_memory: InMemoryWhatsApp,
) -> None:
    _bootstrap_wa_assignment(client, club_suffix="start")
    assert any(m.kind == "template" for m in wa_memory.sent)
    wa_memory.clear()

    occurrence = db.scalar(select(PlayerOccurrence).limit(1))
    assert occurrence is not None
    assert occurrence.status == OccurrenceStatus.PENDING

    response = _post_webhook(
        client,
        _message_envelope(
            {
                "from": "15551234567",
                "id": "wamid.start",
                "timestamp": "1",
                "type": "button",
                "button": {"payload": "START", "text": "Start"},
            }
        ),
    )
    assert response.status_code == 200

    db.expire_all()
    occurrence = db.get(PlayerOccurrence, occurrence.id)
    assert occurrence is not None
    assert occurrence.status == OccurrenceStatus.IN_PROGRESS
    assert occurrence.cursor == 0
    assert any(m.kind == "buttons" for m in wa_memory.sent)


def test_list_reply_stores_draft_and_advances_cursor(
    client: TestClient,
    superadmin: User,
    db: Session,
    wa_memory: InMemoryWhatsApp,
) -> None:
    _bootstrap_wa_assignment(client, club_suffix="list")
    occurrence = db.scalar(select(PlayerOccurrence).limit(1))
    assert occurrence is not None

    _post_webhook(
        client,
        _message_envelope(
            {
                "from": "15551234567",
                "id": "wamid.s",
                "timestamp": "1",
                "type": "button",
                "button": {"payload": "START", "text": "Start"},
            }
        ),
    )
    wa_memory.clear()

    yes_id = reply_id(
        occurrence_id=occurrence.id, question_id="ready", value="yes"
    )
    _post_webhook(
        client,
        _message_envelope(
            {
                "from": "15551234567",
                "id": "wamid.ready",
                "timestamp": "2",
                "type": "interactive",
                "interactive": {
                    "type": "button_reply",
                    "button_reply": {"id": yes_id, "title": "Yes"},
                },
            }
        ),
    )

    db.expire_all()
    occurrence = db.get(PlayerOccurrence, occurrence.id)
    assert occurrence is not None
    assert occurrence.draft_answers == {"ready": True}
    assert occurrence.cursor == 1
    assert any(m.kind == "list" for m in wa_memory.sent)


def test_text_message_does_not_change_draft(
    client: TestClient,
    superadmin: User,
    db: Session,
    wa_memory: InMemoryWhatsApp,
) -> None:
    _bootstrap_wa_assignment(client, club_suffix="text")
    occurrence = db.scalar(select(PlayerOccurrence).limit(1))
    assert occurrence is not None

    _post_webhook(
        client,
        _message_envelope(
            {
                "from": "15551234567",
                "id": "wamid.s",
                "timestamp": "1",
                "type": "button",
                "button": {"payload": "START", "text": "Start"},
            }
        ),
    )
    yes_id = reply_id(
        occurrence_id=occurrence.id, question_id="ready", value="yes"
    )
    _post_webhook(
        client,
        _message_envelope(
            {
                "from": "15551234567",
                "id": "wamid.ready",
                "timestamp": "2",
                "type": "interactive",
                "interactive": {
                    "type": "button_reply",
                    "button_reply": {"id": yes_id, "title": "Yes"},
                },
            }
        ),
    )
    db.expire_all()
    occurrence = db.get(PlayerOccurrence, occurrence.id)
    assert occurrence is not None
    before_draft = dict(occurrence.draft_answers)
    before_cursor = occurrence.cursor
    wa_memory.clear()

    _post_webhook(
        client,
        _message_envelope(
            {
                "from": "15551234567",
                "id": "wamid.txt",
                "timestamp": "3",
                "type": "text",
                "text": {"body": "hello"},
            }
        ),
    )

    db.expire_all()
    occurrence = db.get(PlayerOccurrence, occurrence.id)
    assert occurrence is not None
    assert occurrence.draft_answers == before_draft
    assert occurrence.cursor == before_cursor
    assert any(m.kind == "list" for m in wa_memory.sent)


def test_full_survey_one_response_second_tap_no_duplicate(
    client: TestClient,
    superadmin: User,
    db: Session,
    wa_memory: InMemoryWhatsApp,
) -> None:
    _bootstrap_wa_assignment(client, club_suffix="full")
    occurrence = db.scalar(select(PlayerOccurrence).limit(1))
    assert occurrence is not None
    oid = occurrence.id

    _post_webhook(
        client,
        _message_envelope(
            {
                "from": "15551234567",
                "id": "wamid.s",
                "timestamp": "1",
                "type": "button",
                "button": {"payload": "START", "text": "Start"},
            }
        ),
    )
    for raw_id, title, itype, key in [
        (
            reply_id(occurrence_id=oid, question_id="ready", value="yes"),
            "Yes",
            "button_reply",
            "button_reply",
        ),
        (
            reply_id(occurrence_id=oid, question_id="energy", value="4"),
            "4",
            "list_reply",
            "list_reply",
        ),
        (
            reply_id(occurrence_id=oid, question_id="focus", value="speed"),
            "Speed",
            "list_reply",
            "list_reply",
        ),
    ]:
        _post_webhook(
            client,
            _message_envelope(
                {
                    "from": "15551234567",
                    "id": f"wamid.{raw_id}",
                    "timestamp": "2",
                    "type": "interactive",
                    "interactive": {
                        "type": itype,
                        key: {"id": raw_id, "title": title},
                    },
                }
            ),
        )

    db.expire_all()
    occurrence = db.get(PlayerOccurrence, oid)
    assert occurrence is not None
    assert occurrence.status == OccurrenceStatus.COMPLETED
    responses = list(db.scalars(select(Response).where(Response.occurrence_id == oid)))
    assert len(responses) == 1
    assert responses[0].answers == {
        "ready": True,
        "energy": 4,
        "focus": "speed",
    }
    assert responses[0].channel.value == "whatsapp"

    wa_memory.clear()
    # Second START after complete
    _post_webhook(
        client,
        _message_envelope(
            {
                "from": "15551234567",
                "id": "wamid.again",
                "timestamp": "9",
                "type": "button",
                "button": {"payload": "START", "text": "Start"},
            }
        ),
    )
    db.expire_all()
    responses = list(db.scalars(select(Response).where(Response.occurrence_id == oid)))
    assert len(responses) == 1
    assert any(
        m.kind == "text" and m.body == "Already submitted" for m in wa_memory.sent
    )


def test_status_callback_updates_delivery(
    client: TestClient,
    superadmin: User,
    db: Session,
    wa_memory: InMemoryWhatsApp,
) -> None:
    _bootstrap_wa_assignment(client, club_suffix="status")
    delivery = db.scalar(
        select(Delivery).where(Delivery.kind == DeliveryKind.SURVEY_START)
    )
    assert delivery is not None
    assert delivery.provider_message_id
    mid = delivery.provider_message_id

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA",
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {
                                    "id": mid,
                                    "status": "delivered",
                                    "timestamp": "1",
                                    "recipient_id": "15551234567",
                                }
                            ]
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    assert _post_webhook(client, payload).status_code == 200
    db.expire_all()
    delivery = db.get(Delivery, delivery.id)
    assert delivery is not None
    assert delivery.status.value == "delivered"
