from __future__ import annotations

import re

from fastapi import HTTPException, status

# E.164: + then country code (non-zero) and subscriber number, max 15 digits total.
_E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")


def validate_e164(phone: str | None) -> str | None:
    if phone is None or phone == "":
        return None
    if not _E164_RE.match(phone):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="phone_e164 must be a valid E.164 number",
        )
    return phone
