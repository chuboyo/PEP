from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger("pep.invites")


class InviteDelivery(Protocol):
    def deliver(self, *, email: str, invite_link: str) -> None: ...


class LogInviteDelivery:
    """Dev/ops visibility without writing the invite credential to logs.

    The raw invite URL is a secret (usable at POST /auth/accept-invite). Callers
    return it once in the API response for copy/share in the UI.
    """

    def deliver(self, *, email: str, invite_link: str) -> None:
        del invite_link  # intentionally unused — never log the token
        logger.info("Invite created for %s (link returned in API response only)", email)


default_invite_delivery: InviteDelivery = LogInviteDelivery()
