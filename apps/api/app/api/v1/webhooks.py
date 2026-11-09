from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.ports.whatsapp import get_whatsapp_port
from app.services import whatsapp_survey

logger = logging.getLogger("pep.whatsapp")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_signature(*, app_secret: str, raw_body: bytes, header: str | None) -> bool:
    if not app_secret or not header:
        return False
    if not header.startswith("sha256="):
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(header, f"sha256={expected}")


@router.get("/whatsapp")
def verify_whatsapp_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
) -> Response:
    settings = get_settings()
    if (
        hub_mode == "subscribe"
        and hub_verify_token
        and settings.whatsapp_verify_token
        and hub_verify_token == settings.whatsapp_verify_token
        and hub_challenge is not None
    ):
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.post("/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    settings = get_settings()
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not _verify_signature(
        app_secret=settings.whatsapp_app_secret,
        raw_body=raw_body,
        header=signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    try:
        payload: dict[str, Any] = json.loads(raw_body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        ) from exc

    port = get_whatsapp_port()
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for status_item in value.get("statuses") or []:
                message_id = status_item.get("id")
                status_value = status_item.get("status")
                if message_id and status_value:
                    whatsapp_survey.apply_status_callback(
                        db,
                        provider_message_id=str(message_id),
                        status_value=str(status_value),
                    )
            for message in value.get("messages") or []:
                _dispatch_message(db, message=message, port=port)

    return {"status": "ok"}


def _dispatch_message(db: Session, *, message: dict[str, Any], port: Any) -> None:
    sender = str(message.get("from") or "")
    message_type = str(message.get("type") or "")
    button_payload: str | None = None
    interactive_reply_id: str | None = None

    if message_type == "button":
        button = message.get("button") or {}
        button_payload = button.get("payload") or button.get("text")
    elif message_type == "interactive":
        interactive = message.get("interactive") or {}
        itype = interactive.get("type")
        if itype == "button_reply":
            interactive_reply_id = (interactive.get("button_reply") or {}).get("id")
        elif itype == "list_reply":
            interactive_reply_id = (interactive.get("list_reply") or {}).get("id")

    try:
        whatsapp_survey.handle_inbound_message(
            db,
            sender=sender,
            message_type=message_type,
            button_payload=button_payload,
            interactive_reply_id=interactive_reply_id,
            channel=port,
        )
    except Exception:
        logger.exception("Failed processing WhatsApp inbound message")
