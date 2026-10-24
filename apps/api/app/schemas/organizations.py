from __future__ import annotations

import uuid

from pydantic import BaseModel


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    sport: str | None
    country: str | None
    location: str | None
    logo_url: str | None
    contact_email: str | None
    status: str
