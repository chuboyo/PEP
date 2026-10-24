from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MembershipOut(BaseModel):
    organization_id: uuid.UUID
    role: str
    status: str


class MeResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    platform_role: str | None
    memberships: list[MembershipOut]
