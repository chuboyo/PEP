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


class AssignmentTargetType(str, enum.Enum):
    TEAM = "team"
    PLAYERS = "players"


class AssignmentSchedule(str, enum.Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


class AssignmentChannel(str, enum.Enum):
    IN_APP = "in_app"
    WHATSAPP = "whatsapp"


class OccurrenceStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MISSED = "missed"


class RoutineAssignmentStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class DeliveryKind(str, enum.Enum):
    SURVEY_START = "survey_start"
    QUESTION = "question"
    REMINDER = "reminder"


class DeliveryStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    RESPONDED = "responded"
    FAILED = "failed"
