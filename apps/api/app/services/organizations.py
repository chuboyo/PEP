from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.principal import Principal
from app.models import (
    MembershipRole,
    MembershipStatus,
    OccurrenceStatus,
    UserStatus,
)
from app.repositories import assignments as assignments_repo
from app.repositories import organizations as orgs_repo
from app.repositories import routines as routines_repo
from app.repositories import users as users_repo
from app.schemas.dashboard import RoutineCountsOut
from app.schemas.organizations import CoachListItem, OrganizationMetricsOut


def get_organization_metrics(
    db: Session, *, organization_id: uuid.UUID
) -> OrganizationMetricsOut:
    organization = orgs_repo.get_organization_by_id(db, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    coach_count = orgs_repo.count_memberships(
        db,
        organization_id=organization_id,
        role=MembershipRole.COACH,
        statuses=[MembershipStatus.ACTIVE],
    )
    player_count = orgs_repo.count_memberships(
        db,
        organization_id=organization_id,
        role=MembershipRole.PLAYER,
        statuses=[MembershipStatus.INVITED, MembershipStatus.ACTIVE],
    )
    active_player_count = orgs_repo.count_memberships(
        db,
        organization_id=organization_id,
        role=MembershipRole.PLAYER,
        statuses=[MembershipStatus.ACTIVE],
    )
    questionnaire_completed_count = orgs_repo.count_occurrences(
        db,
        organization_id=organization_id,
        status=OccurrenceStatus.COMPLETED,
    )
    questionnaire_occurrence_count = orgs_repo.count_occurrences(
        db, organization_id=organization_id
    )
    player_ids = orgs_repo.list_player_ids_in_organization(
        db,
        organization_id=organization_id,
        statuses=[MembershipStatus.INVITED, MembershipStatus.ACTIVE],
    )
    routine_counts = RoutineCountsOut(
        **routines_repo.count_statuses_for_team_roster(
            db,
            organization_id=organization_id,
            player_ids=player_ids,
        )
    )
    return OrganizationMetricsOut(
        organization_id=organization_id,
        coach_count=coach_count,
        player_count=player_count,
        active_player_count=active_player_count,
        questionnaire_completed_count=questionnaire_completed_count,
        questionnaire_occurrence_count=questionnaire_occurrence_count,
        routine_counts=routine_counts,
    )


def list_coaches(
    db: Session, *, organization_id: uuid.UUID
) -> list[CoachListItem]:
    rows = orgs_repo.list_coaches_for_organization(
        db, organization_id=organization_id
    )
    return [
        CoachListItem(
            user_id=user.id,
            name=user.name,
            email=user.email,
            status=membership.status.value,
        )
        for user, membership in rows
    ]


def deactivate_coach(
    db: Session,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    membership = orgs_repo.get_membership_for_org_role(
        db,
        organization_id=organization_id,
        user_id=user_id,
        role=MembershipRole.COACH,
    )
    if membership is None or membership.status == MembershipStatus.DEACTIVATED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    user = users_repo.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    membership.status = MembershipStatus.DEACTIVATED
    user.status = UserStatus.DEACTIVATED
    db.commit()


def deactivate_player(
    db: Session,
    *,
    principal: Principal,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    organization = orgs_repo.get_organization_by_id(db, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    membership = orgs_repo.get_membership_for_org_role(
        db,
        organization_id=organization_id,
        user_id=user_id,
        role=MembershipRole.PLAYER,
    )
    if membership is None or membership.status == MembershipStatus.DEACTIVATED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    role = principal.active_role_in(organization_id)
    is_club_admin = role == MembershipRole.CLUB_ADMIN.value
    is_sharing_coach = (
        principal.active_coach_organization_id == organization_id
        and assignments_repo.player_shares_team_with_coach(
            db,
            coach_user_id=principal.user_id,
            player_user_id=user_id,
            organization_id=organization_id,
        )
    )
    if not is_club_admin and not is_sharing_coach:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    user = users_repo.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    membership.status = MembershipStatus.DEACTIVATED
    user.status = UserStatus.DEACTIVATED
    db.commit()
