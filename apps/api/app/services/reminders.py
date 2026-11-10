from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.principal import Principal
from app.models import (
    Assignment,
    AssignmentChannel,
    AssignmentSchedule,
    OccurrenceStatus,
    PlayerOccurrence,
)
from app.ports.whatsapp import WhatsAppPort, get_whatsapp_port
from app.repositories import assignments as assignments_repo
from app.repositories import deliveries as deliveries_repo
from app.repositories import users as users_repo
from app.services import whatsapp_survey

logger = logging.getLogger("pep.reminders")

REMINDER_WINDOW = timedelta(hours=24)


def run_reminder_job(
    db: Session, *, whatsapp: WhatsAppPort | None = None
) -> dict[str, int]:
    """Mark missed, send due reminders, spawn next recurring occurrences."""
    now = datetime.now(UTC)
    missed = _mark_missed(db, now=now)
    reminded = _send_eligible_reminders(db, now=now, whatsapp=whatsapp)
    spawned = _spawn_recurring_occurrences(db, now=now)
    db.commit()
    return {
        "missed_count": missed,
        "reminded_count": reminded,
        "spawned_count": spawned,
    }


def remind_occurrence(
    db: Session,
    *,
    principal: Principal,
    occurrence_id: uuid.UUID,
    whatsapp: WhatsAppPort | None = None,
) -> None:
    org_id = principal.active_coach_organization_id
    if org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    occurrence = assignments_repo.get_occurrence_by_id(db, occurrence_id)
    if occurrence is None or occurrence.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    assignment = assignments_repo.get_assignment_by_id(db, occurrence.assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if not assignments_repo.player_shares_team_with_coach(
        db,
        coach_user_id=principal.user_id,
        player_user_id=occurrence.player_id,
        organization_id=org_id,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if assignment.channel != AssignmentChannel.WHATSAPP:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reminders are only supported for WhatsApp assignments",
        )

    now = datetime.now(UTC)
    if not _is_remindable_status(occurrence) or not _due_in_reminder_window(
        occurrence, now=now
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Occurrence is not eligible for reminder",
        )

    since = now - REMINDER_WINDOW
    if deliveries_repo.has_reminder_since(
        db, occurrence_id=occurrence.id, since=since
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reminder already sent within the last 24 hours",
        )

    _dispatch_reminder_for_occurrence(
        db, occurrence=occurrence, assignment=assignment, whatsapp=whatsapp
    )
    db.commit()


def _mark_missed(db: Session, *, now: datetime) -> int:
    cutoff = now - REMINDER_WINDOW
    rows = assignments_repo.list_pending_past_due(db, older_than=cutoff)
    for occurrence in rows:
        occurrence.status = OccurrenceStatus.MISSED
    return len(rows)


def _send_eligible_reminders(
    db: Session, *, now: datetime, whatsapp: WhatsAppPort | None
) -> int:
    window_start = now - REMINDER_WINDOW
    rows = assignments_repo.list_occurrences_due_in_window(
        db, window_start=window_start, window_end=now
    )
    count = 0
    for occurrence, assignment in rows:
        if assignment.channel != AssignmentChannel.WHATSAPP:
            continue
        if deliveries_repo.has_reminder_since(
            db, occurrence_id=occurrence.id, since=window_start
        ):
            continue
        if _dispatch_reminder_for_occurrence(
            db, occurrence=occurrence, assignment=assignment, whatsapp=whatsapp
        ):
            count += 1
            db.commit()
    return count


def _dispatch_reminder_for_occurrence(
    db: Session,
    *,
    occurrence: PlayerOccurrence,
    assignment: Assignment,
    whatsapp: WhatsAppPort | None,
) -> bool:
    player = users_repo.get_user_by_id(db, occurrence.player_id)
    if player is None or not player.phone_e164:
        logger.info(
            "Skipping reminder for occurrence %s: missing phone", occurrence.id
        )
        return False

    questionnaire_name = (
        assignments_repo.get_questionnaire_name(db, assignment.questionnaire_id)
        or "Questionnaire"
    )
    delivery = whatsapp_survey.queue_reminder_delivery(db, occurrence=occurrence)
    db.flush()
    wa_port = whatsapp or get_whatsapp_port()
    whatsapp_survey.dispatch_queued_reminder(
        db,
        delivery_id=delivery.id,
        player_name=player.name,
        questionnaire_name=questionnaire_name,
        to_e164=player.phone_e164,
        channel=wa_port,
    )
    return True


def _spawn_recurring_occurrences(db: Session, *, now: datetime) -> int:
    spawned = 0
    for assignment in assignments_repo.list_recurring_assignments(db):
        delta = (
            timedelta(days=1)
            if assignment.schedule == AssignmentSchedule.DAILY
            else timedelta(days=7)
        )
        for player_id in assignments_repo.list_assignment_target_ids(
            db, assignment_id=assignment.id
        ):
            latest = assignments_repo.get_latest_occurrence_for_assignment_player(
                db, assignment_id=assignment.id, player_id=player_id
            )
            if latest is None or latest.due_at is None:
                continue
            if not _window_closed(latest, now=now):
                continue
            next_due = latest.due_at + delta
            if assignment.ends_on is not None and next_due.date() > assignment.ends_on:
                continue
            next_window_start = latest.due_at
            if assignments_repo.occurrence_exists_for_window(
                db,
                assignment_id=assignment.id,
                player_id=player_id,
                window_start=next_window_start,
            ):
                continue
            assignments_repo.create_occurrence(
                db,
                assignment_id=assignment.id,
                organization_id=assignment.organization_id,
                player_id=player_id,
                window_start=next_window_start,
                due_at=next_due,
            )
            spawned += 1
    return spawned


def _window_closed(occurrence: PlayerOccurrence, *, now: datetime) -> bool:
    if occurrence.status in (
        OccurrenceStatus.COMPLETED,
        OccurrenceStatus.MISSED,
    ):
        return True
    if occurrence.due_at is None:
        return False
    return occurrence.due_at + REMINDER_WINDOW <= now


def _is_remindable_status(occurrence: PlayerOccurrence) -> bool:
    return occurrence.status in (
        OccurrenceStatus.PENDING,
        OccurrenceStatus.IN_PROGRESS,
    )


def _due_in_reminder_window(occurrence: PlayerOccurrence, *, now: datetime) -> bool:
    if occurrence.due_at is None:
        return False
    return now - REMINDER_WINDOW <= occurrence.due_at <= now
