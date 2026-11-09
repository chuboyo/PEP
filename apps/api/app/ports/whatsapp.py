from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.core.config import get_settings

logger = logging.getLogger("pep.whatsapp")


@dataclass(frozen=True)
class InteractiveButton:
    id: str
    title: str


@dataclass(frozen=True)
class InteractiveListRow:
    id: str
    title: str


@dataclass
class OutboundMessage:
    kind: str
    to_e164: str
    body: str | None = None
    template_name: str | None = None
    body_params: list[str] = field(default_factory=list)
    buttons: list[InteractiveButton] = field(default_factory=list)
    list_rows: list[InteractiveListRow] = field(default_factory=list)
    list_button_label: str | None = None
    provider_message_id: str = ""


class WhatsAppPort(Protocol):
    def send_template(
        self,
        *,
        to_e164: str,
        template_name: str,
        body_params: list[str],
    ) -> str:
        """Send an approved template. Returns provider message id."""

    def send_interactive_buttons(
        self,
        *,
        to_e164: str,
        body: str,
        buttons: list[InteractiveButton],
    ) -> str: ...

    def send_interactive_list(
        self,
        *,
        to_e164: str,
        body: str,
        button_label: str,
        rows: list[InteractiveListRow],
    ) -> str: ...

    def send_text(self, *, to_e164: str, body: str) -> str: ...


class InMemoryWhatsApp:
    """Records outbound payloads for tests; never calls Meta."""

    def __init__(self) -> None:
        self.sent: list[OutboundMessage] = []

    def clear(self) -> None:
        self.sent.clear()

    def send_template(
        self,
        *,
        to_e164: str,
        template_name: str,
        body_params: list[str],
    ) -> str:
        message_id = f"mem-{uuid.uuid4()}"
        self.sent.append(
            OutboundMessage(
                kind="template",
                to_e164=to_e164,
                template_name=template_name,
                body_params=list(body_params),
                provider_message_id=message_id,
            )
        )
        return message_id

    def send_interactive_buttons(
        self,
        *,
        to_e164: str,
        body: str,
        buttons: list[InteractiveButton],
    ) -> str:
        message_id = f"mem-{uuid.uuid4()}"
        self.sent.append(
            OutboundMessage(
                kind="buttons",
                to_e164=to_e164,
                body=body,
                buttons=list(buttons),
                provider_message_id=message_id,
            )
        )
        return message_id

    def send_interactive_list(
        self,
        *,
        to_e164: str,
        body: str,
        button_label: str,
        rows: list[InteractiveListRow],
    ) -> str:
        message_id = f"mem-{uuid.uuid4()}"
        self.sent.append(
            OutboundMessage(
                kind="list",
                to_e164=to_e164,
                body=body,
                list_button_label=button_label,
                list_rows=list(rows),
                provider_message_id=message_id,
            )
        )
        return message_id

    def send_text(self, *, to_e164: str, body: str) -> str:
        message_id = f"mem-{uuid.uuid4()}"
        self.sent.append(
            OutboundMessage(
                kind="text",
                to_e164=to_e164,
                body=body,
                provider_message_id=message_id,
            )
        )
        return message_id


class MetaWhatsApp:
    """WhatsApp Cloud API client."""

    def __init__(
        self,
        *,
        token: str,
        phone_number_id: str,
        api_version: str = "v21.0",
    ) -> None:
        self._token = token
        self._phone_number_id = phone_number_id
        self._base = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"

    def _post(self, payload: dict) -> str:
        response = httpx.post(
            self._base,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        messages = data.get("messages") or []
        if not messages:
            raise RuntimeError("WhatsApp API returned no message id")
        return str(messages[0]["id"])

    def send_template(
        self,
        *,
        to_e164: str,
        template_name: str,
        body_params: list[str],
    ) -> str:
        to = to_e164.lstrip("+")
        components = []
        if body_params:
            components.append(
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": param} for param in body_params
                    ],
                }
            )
        return self._post(
            {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en"},
                    "components": components,
                },
            }
        )

    def send_interactive_buttons(
        self,
        *,
        to_e164: str,
        body: str,
        buttons: list[InteractiveButton],
    ) -> str:
        to = to_e164.lstrip("+")
        return self._post(
            {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": body},
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {"id": button.id, "title": button.title[:20]},
                            }
                            for button in buttons
                        ]
                    },
                },
            }
        )

    def send_interactive_list(
        self,
        *,
        to_e164: str,
        body: str,
        button_label: str,
        rows: list[InteractiveListRow],
    ) -> str:
        to = to_e164.lstrip("+")
        return self._post(
            {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {"text": body},
                    "action": {
                        "button": button_label[:20],
                        "sections": [
                            {
                                "title": "Options",
                                "rows": [
                                    {"id": row.id, "title": row.title[:24]}
                                    for row in rows
                                ],
                            }
                        ],
                    },
                },
            }
        )

    def send_text(self, *, to_e164: str, body: str) -> str:
        to = to_e164.lstrip("+")
        return self._post(
            {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": body},
            }
        )


_override: WhatsAppPort | None = None
_memory_singleton = InMemoryWhatsApp()


def set_whatsapp_port(port: WhatsAppPort | None) -> None:
    """Tests inject an InMemoryWhatsApp; pass None to restore defaults."""
    global _override
    _override = port


def get_whatsapp_port() -> WhatsAppPort:
    if _override is not None:
        return _override
    settings = get_settings()
    if settings.whatsapp_token and settings.whatsapp_phone_number_id:
        return MetaWhatsApp(
            token=settings.whatsapp_token,
            phone_number_id=settings.whatsapp_phone_number_id,
        )
    return _memory_singleton
