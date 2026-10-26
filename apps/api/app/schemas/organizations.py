from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    sport: str | None
    country: str | None
    location: str | None
    logo_url: str | None
    contact_email: str | None
    status: str


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1)
    sport: str | None = None
    country: str | None = None
    location: str | None = None
    logo_url: str | None = None
    contact_email: EmailStr | None = None
    admin_name: str = Field(min_length=1)
    admin_email: EmailStr


class OrganizationCreated(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    admin_email: str
    invite_link: str


class OrganizationListItem(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    admin_email: str | None


class CoachInviteCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr


class CoachInviteCreated(BaseModel):
    organization_id: uuid.UUID
    email: str
    invite_link: str
