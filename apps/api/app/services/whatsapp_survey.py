from __future__ import annotations

import copy
import logging
import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    AssignmentChannel,
    Delivery,
    DeliveryKind,
    DeliveryStatus,
    OccurrenceStatus,
    PlayerOccurrence,
)
from app.ports.whatsapp import (
    InteractiveButton,
    InteractiveListRow,
    WhatsAppPort,
    get_whatsapp_port,
)
from app.repositories import assignments as assignments_repo
from app.repositories import deliveries as deliveries_repo
from app.repositories import users as users_repo
from app.schemas.answers import validate_answers

logger = logging.getLogger("pep.whatsapp")


def phone_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def find_user_by_wa_sender(db: Session, sender: str):
    digits = phone_digits(sender)
    if not digits:
        return None
    # Prefer exact E.164 match first, then digit-equal scan of stored phones.
    as_e164 = f"+{digits}" if not sender.startswith("+") else sender
    user = users_repo.get_user_by_phone(db, as_e164)
    if user is not None:
        return user
    # Fallback: compare digits only (Meta often omits '+').
    from sqlalchemy import select

    from app.models import User

    for candidate in db.scalars(select(User).where(User.phone_e164.is_not(None))).all():
        if candidate.phone_e164 and phone_digits(candidate.phone_e164) == digits:
            return candidate
    return None


def reply_id(*, occurrence_id: uuid.UUID, question_id: str, value: str) -> str:
    return f"{occurrence_id}:{question_id}:{value}"


def parse_reply_id(raw: str) -> tuple[uuid.UUID, str, str] | None:
    parts = raw.split(":", 2)
    if len(parts) != 3:
        return None
    try:
        return uuid.UUID(parts[0]), parts[1], parts[2]
    except ValueError:
        return None


def queue_start_delivery(
    db: Session, *, occurrence: PlayerOccurrence
) -> Delivery:
    """Persist a queued survey_start delivery. Call Meta only after commit."""
    return deliveries_repo.create_delivery(
        db,
        occurrence_id=occurrence.id,
        channel=AssignmentChannel.WHATSAPP.value,
        kind=DeliveryKind.SURVEY_START,
        status=DeliveryStatus.QUEUED,
    )


def dispatch_queued_start(
    db: Session,
    *,
    delivery_id: uuid.UUID,
    player_name: str,
    questionnaire_name: str,
    to_e164: str,
    channel: WhatsAppPort | None = None,
) -> None:
    """Send a previously committed queued start template. Never raises to caller.

    Assignment rows must already be committed so a Meta failure cannot roll them
    back. Caller should commit after each dispatch so provider_message_id is
    visible to concurrent status webhooks before the next send.
    """
    port = channel or get_whatsapp_port()
    settings = get_settings()
    delivery = deliveries_repo.get_by_id(db, delivery_id)
    if delivery is None or delivery.status != DeliveryStatus.QUEUED:
        return
    try:
        message_id = port.send_template(
            to_e164=to_e164,
            template_name=settings.whatsapp_template_start,
            body_params=[player_name, questionnaire_name],
        )
        delivery.status = DeliveryStatus.SENT
        delivery.provider_message_id = message_id
    except Exception:
        logger.exception("Failed to send WhatsApp start template")
        delivery.status = DeliveryStatus.FAILED


def _send_question(
    db: Session,
    *,
    occurrence: PlayerOccurrence,
    question: dict[str, Any],
    to_e164: str,
    port: WhatsAppPort,
) -> None:
    prompt = str(question.get("prompt") or question.get("id") or "Question")
    qid = str(question["id"])
    qtype = question["type"]
    delivery = deliveries_repo.create_delivery(
        db,
        occurrence_id=occurrence.id,
        channel=AssignmentChannel.WHATSAPP.value,
        kind=DeliveryKind.QUESTION,
        status=DeliveryStatus.QUEUED,
    )
    try:
        if qtype == "yes_no":
            message_id = port.send_interactive_buttons(
                to_e164=to_e164,
                body=prompt,
                buttons=[
                    InteractiveButton(
                        id=reply_id(
                            occurrence_id=occurrence.id, question_id=qid, value="yes"
                        ),
                        title="Yes",
                    ),
                    InteractiveButton(
                        id=reply_id(
                            occurrence_id=occurrence.id, question_id=qid, value="no"
                        ),
                        title="No",
                    ),
                ],
            )
        elif qtype == "rating":
            min_v = int(question.get("min", 1))
            max_v = int(question.get("max", 5))
            rows = [
                InteractiveListRow(
                    id=reply_id(
                        occurrence_id=occurrence.id,
                        question_id=qid,
                        value=str(n),
                    ),
                    title=str(n),
                )
                for n in range(min_v, max_v + 1)
            ]
            message_id = port.send_interactive_list(
                to_e164=to_e164,
                body=prompt,
                button_label="Rate",
                rows=rows,
            )
        elif qtype == "single_choice":
            options = question.get("options") or []
            rows = [
                InteractiveListRow(
                    id=reply_id(
                        occurrence_id=occurrence.id,
                        question_id=qid,
                        value=str(opt["id"]),
                    ),
                    title=str(opt.get("label") or opt["id"])[:24],
                )
                for opt in options
            ]
            message_id = port.send_interactive_list(
                to_e164=to_e164,
                body=prompt,
                button_label="Choose",
                rows=rows,
            )
        else:
            delivery.status = DeliveryStatus.FAILED
            raise ValueError(f"Unsupported WhatsApp question type: {qtype}")
        delivery.status = DeliveryStatus.SENT
        delivery.provider_message_id = message_id
    except Exception:
        logger.exception("Failed to send WhatsApp question")
        delivery.status = DeliveryStatus.FAILED
        raise


def _current_question(
    questions: list[dict[str, Any]], cursor: int
) -> dict[str, Any] | None:
    if cursor < 0 or cursor >= len(questions):
        return None
    return questions[cursor]


def _coerce_reply_value(question: dict[str, Any], raw: str) -> Any:
    qtype = question["type"]
    if qtype == "yes_no":
        if raw == "yes":
            return True
        if raw == "no":
            return False
        raise ValueError("invalid yes_no")
    if qtype == "rating":
        return int(raw)
    if qtype == "single_choice":
        return raw
    raise ValueError(f"unsupported type {qtype}")


def _complete_occurrence(
    db: Session,
    *,
    occurrence: PlayerOccurrence,
    answers: dict[str, Any],
    questions_snapshot: list[dict[str, Any]],
) -> None:
    assignments_repo.create_response(
        db,
        occurrence_id=occurrence.id,
        organization_id=occurrence.organization_id,
        player_id=occurrence.player_id,
        channel=AssignmentChannel.WHATSAPP,
        answers=answers,
        questions_snapshot=copy.deepcopy(questions_snapshot),
    )
    occurrence.status = OccurrenceStatus.COMPLETED


def handle_inbound_message(
    db: Session,
    *,
    sender: str,
    message_type: str,
    button_payload: str | None = None,
    interactive_reply_id: str | None = None,
    channel: WhatsAppPort | None = None,
) -> None:
    """Process one inbound WhatsApp message (button / interactive / text)."""
    port = channel or get_whatsapp_port()
    user = find_user_by_wa_sender(db, sender)
    if user is None or not user.phone_e164:
        logger.info("Ignoring WhatsApp message from unknown sender")
        return

    to_e164 = user.phone_e164

    if message_type == "button" and (button_payload or "").upper() == "START":
        _handle_start(db, player_id=user.id, to_e164=to_e164, port=port)
        return

    if message_type == "interactive" and interactive_reply_id:
        _handle_interactive_reply(
            db,
            player_id=user.id,
            to_e164=to_e164,
            reply_raw=interactive_reply_id,
            port=port,
        )
        return

    # Typed text or unexpected types: resend current question without changing drafts.
    _resend_current(db, player_id=user.id, to_e164=to_e164, port=port)


def _handle_start(
    db: Session,
    *,
    player_id: uuid.UUID,
    to_e164: str,
    port: WhatsAppPort,
) -> None:
    # Only WhatsApp-channel occurrences — a newer in-app assign must not steal START.
    occurrence = assignments_repo.get_latest_open_occurrence_for_player(
        db, player_id, channel=AssignmentChannel.WHATSAPP
    )
    if occurrence is None:
        latest = assignments_repo.get_latest_occurrence_for_player(
            db, player_id, channel=AssignmentChannel.WHATSAPP
        )
        if latest is not None and latest.status == OccurrenceStatus.COMPLETED:
            port.send_text(to_e164=to_e164, body="Already submitted")
            db.commit()
        return

    assignment = assignments_repo.get_assignment_by_id(db, occurrence.assignment_id)
    if assignment is None or assignment.channel != AssignmentChannel.WHATSAPP:
        return

    questions = assignment.questions_snapshot
    if occurrence.status == OccurrenceStatus.PENDING:
        occurrence.status = OccurrenceStatus.IN_PROGRESS
        occurrence.cursor = 0

    question = _current_question(questions, occurrence.cursor)
    if question is None:
        return
    _send_question(
        db, occurrence=occurrence, question=question, to_e164=to_e164, port=port
    )
    db.commit()


def _handle_interactive_reply(
    db: Session,
    *,
    player_id: uuid.UUID,
    to_e164: str,
    reply_raw: str,
    port: WhatsAppPort,
) -> None:
    parsed = parse_reply_id(reply_raw)
    if parsed is None:
        _resend_current(db, player_id=player_id, to_e164=to_e164, port=port)
        return

    occurrence_id, question_id, raw_value = parsed
    occurrence = assignments_repo.get_occurrence_by_id(db, occurrence_id)
    if occurrence is None or occurrence.player_id != player_id:
        return

    if occurrence.status == OccurrenceStatus.COMPLETED:
        port.send_text(to_e164=to_e164, body="Already submitted")
        db.commit()
        return

    assignment = assignments_repo.get_assignment_by_id(db, occurrence.assignment_id)
    if assignment is None or assignment.channel != AssignmentChannel.WHATSAPP:
        return

    questions = assignment.questions_snapshot
    current = _current_question(questions, occurrence.cursor)
    if current is None or current.get("id") != question_id:
        _resend_current(db, player_id=player_id, to_e164=to_e164, port=port)
        return

    try:
        value = _coerce_reply_value(current, raw_value)
    except ValueError:
        _resend_current(db, player_id=player_id, to_e164=to_e164, port=port)
        return

    draft = dict(occurrence.draft_answers or {})
    draft[question_id] = value
    occurrence.draft_answers = draft
    occurrence.cursor = occurrence.cursor + 1
    if occurrence.status == OccurrenceStatus.PENDING:
        occurrence.status = OccurrenceStatus.IN_PROGRESS

    if occurrence.cursor >= len(questions):
        try:
            normalized = validate_answers(
                questions_snapshot=questions, answers=draft
            )
        except ValueError:
            # Should not happen for interactive-only questionnaires; resend.
            occurrence.cursor = max(0, occurrence.cursor - 1)
            occurrence.draft_answers = {
                k: v for k, v in draft.items() if k != question_id
            }
            _resend_current(db, player_id=player_id, to_e164=to_e164, port=port)
            return
        existing = assignments_repo.get_response_for_occurrence(db, occurrence.id)
        if existing is not None:
            occurrence.status = OccurrenceStatus.COMPLETED
            port.send_text(to_e164=to_e164, body="Already submitted")
            db.commit()
            return
        try:
            _complete_occurrence(
                db,
                occurrence=occurrence,
                answers=normalized,
                questions_snapshot=questions,
            )
        except IntegrityError:
            db.rollback()
            port.send_text(to_e164=to_e164, body="Already submitted")
            return
        port.send_text(to_e164=to_e164, body="Thanks — survey submitted.")
        db.commit()
        return

    next_q = _current_question(questions, occurrence.cursor)
    if next_q is not None:
        _send_question(
            db, occurrence=occurrence, question=next_q, to_e164=to_e164, port=port
        )
    db.commit()


def _resend_current(
    db: Session,
    *,
    player_id: uuid.UUID,
    to_e164: str,
    port: WhatsAppPort,
) -> None:
    occurrence = assignments_repo.get_latest_open_occurrence_for_player(
        db, player_id, channel=AssignmentChannel.WHATSAPP
    )
    if occurrence is None:
        latest = assignments_repo.get_latest_occurrence_for_player(
            db, player_id, channel=AssignmentChannel.WHATSAPP
        )
        if latest is not None and latest.status == OccurrenceStatus.COMPLETED:
            port.send_text(to_e164=to_e164, body="Already submitted")
            db.commit()
        return

    assignment = assignments_repo.get_assignment_by_id(db, occurrence.assignment_id)
    if assignment is None or assignment.channel != AssignmentChannel.WHATSAPP:
        return
    question = _current_question(assignment.questions_snapshot, occurrence.cursor)
    if question is None:
        return
    _send_question(
        db, occurrence=occurrence, question=question, to_e164=to_e164, port=port
    )
    db.commit()


def apply_status_callback(
    db: Session,
    *,
    provider_message_id: str,
    status_value: str,
) -> None:
    delivery = deliveries_repo.get_by_provider_message_id(db, provider_message_id)
    if delivery is None:
        return
    mapping = {
        "sent": DeliveryStatus.SENT,
        "delivered": DeliveryStatus.DELIVERED,
        "read": DeliveryStatus.READ,
        "failed": DeliveryStatus.FAILED,
    }
    new_status = mapping.get(status_value.lower())
    if new_status is None:
        return
    delivery.status = new_status
    db.commit()
