from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger("pep.invites")


class InviteDelivery(Protocol):
    def deliver(self, *, email: str, invite_link: str) -> None: ...


class LogInviteDelivery:
    def deliver(self, *, email: str, invite_link: str) -> None:
        logger.info("Invite for %s: %s", email, invite_link)


default_invite_delivery: InviteDelivery = LogInviteDelivery()
