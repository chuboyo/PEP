from __future__ import annotations

import enum


class UserStatus(str, enum.Enum):
    INVITED = "invited"
    ACTIVE = "active"
    DEACTIVATED = "deactivated"


class PlatformRole(str, enum.Enum):
    SUPERADMIN = "SUPERADMIN"


class OrganizationStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class MembershipRole(str, enum.Enum):
    CLUB_ADMIN = "CLUB_ADMIN"
    COACH = "COACH"
    PLAYER = "PLAYER"


class MembershipStatus(str, enum.Enum):
    INVITED = "invited"
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
