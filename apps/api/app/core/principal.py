from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MembershipInfo:
    organization_id: uuid.UUID
    role: str
    status: str


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    platform_role: str | None
    memberships: list[MembershipInfo] = field(default_factory=list)
    team_ids: list[uuid.UUID] = field(default_factory=list)

    @property
    def is_superadmin(self) -> bool:
        return self.platform_role == "SUPERADMIN"

    def has_active_membership(self, organization_id: uuid.UUID) -> bool:
        return any(
            m.organization_id == organization_id and m.status == "active"
            for m in self.memberships
        )

    def active_role_in(self, organization_id: uuid.UUID) -> str | None:
        for m in self.memberships:
            if m.organization_id == organization_id and m.status == "active":
                return m.role
        return None
