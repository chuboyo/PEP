from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class TeamCreate(BaseModel):
    name: str = Field(min_length=1)


class TeamOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str


class TeamMemberOut(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    role: str | None
    phone_e164: str | None = None


class TeamDetailOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    members: list[TeamMemberOut]


class PlayerInviteCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    phone_e164: str | None = None


class PlayerInviteCreated(BaseModel):
    organization_id: uuid.UUID
    team_id: uuid.UUID
    email: str
    invite_link: str
