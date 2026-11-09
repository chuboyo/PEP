from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Delivery, DeliveryKind, DeliveryStatus


def create_delivery(
    db: Session,
    *,
    occurrence_id: uuid.UUID,
    channel: str,
    kind: DeliveryKind,
    status: DeliveryStatus,
    provider_message_id: str | None = None,
) -> Delivery:
    row = Delivery(
        occurrence_id=occurrence_id,
        channel=channel,
        kind=kind,
        status=status,
        provider_message_id=provider_message_id,
    )
    db.add(row)
    db.flush()
    return row


def get_by_id(db: Session, delivery_id: uuid.UUID) -> Delivery | None:
    return db.get(Delivery, delivery_id)


def get_by_provider_message_id(
    db: Session, provider_message_id: str
) -> Delivery | None:
    return db.scalar(
        select(Delivery).where(Delivery.provider_message_id == provider_message_id)
    )


def list_for_occurrence(db: Session, occurrence_id: uuid.UUID) -> list[Delivery]:
    return list(
        db.scalars(
            select(Delivery)
            .where(Delivery.occurrence_id == occurrence_id)
            .order_by(Delivery.created_at.asc())
        ).all()
    )
