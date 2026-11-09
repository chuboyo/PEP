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
    Assignment,
    Delivery,
    DeliveryKind,
    DeliveryStatus,
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


class _FailAfterFirstTemplate(InMemoryWhatsApp):
    """Succeeds the first template send, then raises (simulates Meta mid-loop failure)."""

    def __init__(self) -> None:
        super().__init__()
        self._template_calls = 0

    def send_template(
        self,
        *,
        to_e164: str,
        template_name: str,
        body_params: list[str],
    ) -> str:
        self._template_calls += 1
        if self._template_calls >= 2:
            raise RuntimeError("simulated Meta failure")
        return super().send_template(
            to_e164=to_e164,
            template_name=template_name,
            body_params=body_params,
        )


class _FailFirstQuestionSend(InMemoryWhatsApp):
    """First interactive send fails; later ones succeed (same webhook batch)."""

    def __init__(self) -> None:
        super().__init__()
        self._fail_next_interactive = True

    def send_interactive_buttons(self, **kwargs: object) -> str:  # type: ignore[override]
        if self._fail_next_interactive:
            self._fail_next_interactive = False
            raise RuntimeError("simulated question send failure")
        return super().send_interactive_buttons(**kwargs)  # type: ignore[arg-type]

    def send_interactive_list(self, **kwargs: object) -> str:  # type: ignore[override]
        if self._fail_next_interactive:
            self._fail_next_interactive = False
            raise RuntimeError("simulated question send failure")
        return super().send_interactive_list(**kwargs)  # type: ignore[arg-type]

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


def test_whatsapp_assign_commits_before_send_partial_failure(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    """If a later Meta send fails, earlier players keep a durable assignment.

    Commit-then-send: the HTTP assign succeeds, occurrences remain, the first
    delivery is SENT with a provider id, and the failed one is FAILED — not rolled
    back (which would leave ghost WhatsApp messages for a missing assignment).
    """
    port = _FailAfterFirstTemplate()
    set_whatsapp_port(port)
    try:
        coach_headers, _ = bootstrap_coach(
            client,
            club_name="Partial WA FC",
            admin_email="partial-wa-admin@example.com",
            coach_email="partial-wa-coach@example.com",
        )
        created = client.post(
            "/api/v1/questionnaires",
            headers=coach_headers,
            json={
                "name": "Partial WA",
                "questions": _three_question_payload()[:1],
            },
        )
        assert created.status_code == 200
        team = client.post(
            "/api/v1/teams",
            headers=coach_headers,
            json={"name": "Partial Team"},
        ).json()
        for i, phone in enumerate(["+15550001001", "+15550001002"]):
            invite = client.post(
                f"/api/v1/teams/{team['id']}/players",
                headers=coach_headers,
                json={
                    "name": f"Player {i}",
                    "email": f"partial-wa-{i}@example.com",
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
                "questionnaire_id": created.json()["id"],
                "target_type": "team",
                "team_id": team["id"],
                "due_at": due,
                "channel": "whatsapp",
            },
        )
        assert assigned.status_code == 200, assigned.text
        assert assigned.json()["occurrence_count"] == 2
        assignment_id = assigned.json()["id"]

        db.expire_all()
        assert db.get(Assignment, assignment_id) is not None
        occurrences = list(
            db.scalars(
                select(PlayerOccurrence).where(
                    PlayerOccurrence.assignment_id == assignment_id
                )
            )
        )
        assert len(occurrences) == 2
        deliveries = list(
            db.scalars(
                select(Delivery).where(
                    Delivery.occurrence_id.in_([o.id for o in occurrences])
                )
            )
        )
        assert len(deliveries) == 2
        statuses = {d.status for d in deliveries}
        assert DeliveryStatus.SENT in statuses
        assert DeliveryStatus.FAILED in statuses
        sent = next(d for d in deliveries if d.status == DeliveryStatus.SENT)
        assert sent.provider_message_id
        assert len(port.sent) == 1
    finally:
        set_whatsapp_port(None)


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


def test_webhook_rolls_back_dirty_session_on_handler_error(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    """A failed message must not leave dirty rows for a later commit in-batch."""
    port = _FailFirstQuestionSend()
    set_whatsapp_port(port)
    try:
        _bootstrap_wa_assignment(
            client, club_suffix="dirty-session", phone="+15559876543"
        )
        db.expire_all()
        occurrence = db.scalar(select(PlayerOccurrence).limit(1))
        assert occurrence is not None
        occurrence_id = occurrence.id
        assert occurrence.status == OccurrenceStatus.PENDING

        # Same HTTP request: first START mutates then fails; second START commits.
        # Without rollback, the failed attempt's delivery/status ride the 2nd commit.
        batch = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WABA",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "from": "15559876543",
                                        "id": "wamid.dirty-start-1",
                                        "timestamp": "1",
                                        "type": "button",
                                        "button": {
                                            "payload": "START",
                                            "text": "Start",
                                        },
                                    },
                                    {
                                        "from": "15559876543",
                                        "id": "wamid.dirty-start-2",
                                        "timestamp": "2",
                                        "type": "button",
                                        "button": {
                                            "payload": "START",
                                            "text": "Start",
                                        },
                                    },
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }
        assert _post_webhook(client, batch).status_code == 200

        db.expire_all()
        occurrence = db.get(PlayerOccurrence, occurrence_id)
        assert occurrence is not None
        assert occurrence.status == OccurrenceStatus.IN_PROGRESS
        assert occurrence.cursor == 0
        question_deliveries = list(
            db.scalars(
                select(Delivery).where(
                    Delivery.occurrence_id == occurrence_id,
                    Delivery.kind == DeliveryKind.QUESTION,
                )
            )
        )
        # Only the successful second START should leave a question delivery.
        assert len(question_deliveries) == 1
        assert question_deliveries[0].status == DeliveryStatus.SENT
    finally:
        set_whatsapp_port(None)


def test_start_ignores_newer_in_app_assignment(
    client: TestClient,
    superadmin: User,
    db: Session,
    wa_memory: InMemoryWhatsApp,
) -> None:
    """START must bind to the WhatsApp occurrence, not a newer in-app one."""
    coach_headers, team_id, _, questionnaire_id = _bootstrap_wa_assignment(
        client, club_suffix="channel-steal", phone="+15557654321"
    )
    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    # Newer in-app assignment with short_text would break WA sends if START stole it.
    short_q = client.post(
        "/api/v1/questionnaires",
        headers=coach_headers,
        json={
            "name": "In-app notes",
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
    assert short_q.status_code == 200
    in_app = client.post(
        "/api/v1/assignments",
        headers=coach_headers,
        json={
            "questionnaire_id": short_q.json()["id"],
            "target_type": "team",
            "team_id": team_id,
            "due_at": due,
            "channel": "in_app",
        },
    )
    assert in_app.status_code == 200

    db.expire_all()
    wa_occ = db.scalar(
        select(PlayerOccurrence)
        .join(Assignment, Assignment.id == PlayerOccurrence.assignment_id)
        .where(Assignment.channel == "whatsapp")
        .limit(1)
    )
    in_app_occ = db.scalar(
        select(PlayerOccurrence)
        .join(Assignment, Assignment.id == PlayerOccurrence.assignment_id)
        .where(Assignment.channel == "in_app")
        .limit(1)
    )
    assert wa_occ is not None and in_app_occ is not None
    assert in_app_occ.created_at >= wa_occ.created_at

    wa_memory.clear()
    response = _post_webhook(
        client,
        _message_envelope(
            {
                "from": "15557654321",
                "id": "wamid.start-channel",
                "timestamp": "1",
                "type": "button",
                "button": {"payload": "START", "text": "Start"},
            }
        ),
    )
    assert response.status_code == 200

    db.expire_all()
    wa_occ = db.get(PlayerOccurrence, wa_occ.id)
    in_app_occ = db.get(PlayerOccurrence, in_app_occ.id)
    assert wa_occ is not None and in_app_occ is not None
    assert wa_occ.status == OccurrenceStatus.IN_PROGRESS
    assert in_app_occ.status == OccurrenceStatus.PENDING
    assert any(m.kind == "buttons" for m in wa_memory.sent)


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


def test_provider_message_id_committed_per_send(
    client: TestClient,
    superadmin: User,
    db: Session,
) -> None:
    """After each template send, provider_message_id must be queryable (not batched)."""
    from unittest.mock import patch

    from sqlalchemy.orm import Session as SaSession

    port = InMemoryWhatsApp()
    set_whatsapp_port(port)
    visible_mids: list[str] = []
    orig_commit = SaSession.commit

    def commit_and_assert_sent_ids_visible(self: SaSession, *args: object, **kwargs: object):
        result = orig_commit(self, *args, **kwargs)
        db.expire_all()
        for msg in port.sent:
            found = db.scalar(
                select(Delivery).where(
                    Delivery.provider_message_id == msg.provider_message_id
                )
            )
            if found is not None:
                visible_mids.append(msg.provider_message_id)
        return result

    try:
        coach_headers, _ = bootstrap_coach(
            client,
            club_name="PerSend FC",
            admin_email="persend-admin@example.com",
            coach_email="persend-coach@example.com",
        )
        created = client.post(
            "/api/v1/questionnaires",
            headers=coach_headers,
            json={
                "name": "PerSend",
                "questions": _three_question_payload()[:1],
            },
        )
        assert created.status_code == 200
        team = client.post(
            "/api/v1/teams",
            headers=coach_headers,
            json={"name": "PerSend Team"},
        ).json()
        for i, phone in enumerate(["+15550002001", "+15550002002"]):
            invite = client.post(
                f"/api/v1/teams/{team['id']}/players",
                headers=coach_headers,
                json={
                    "name": f"P{i}",
                    "email": f"persend-{i}@example.com",
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

        due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        with patch.object(SaSession, "commit", commit_and_assert_sent_ids_visible):
            assigned = client.post(
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
        assert assigned.status_code == 200, assigned.text
        assert len(port.sent) == 2
        # First send's id must appear in a visibility check before the second
        # send finishes — i.e. committed mid-loop, not only at the end.
        assert port.sent[0].provider_message_id in visible_mids
        assert visible_mids.index(port.sent[0].provider_message_id) < len(visible_mids)
        assert port.sent[1].provider_message_id in visible_mids
    finally:
        set_whatsapp_port(None)
