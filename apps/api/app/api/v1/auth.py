from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_principal
from app.core.principal import Principal
from app.db.session import get_db
from app.repositories import users as users_repo
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MeResponse,
    MembershipOut,
    RefreshRequest,
    TokenResponse,
)
from app.services import auth as auth_service

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return auth_service.login(db, body.email, body.password)


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return auth_service.refresh(db, body.refresh_token)


@router.post("/auth/logout", status_code=204, response_class=Response)
def logout(body: LogoutRequest, db: Session = Depends(get_db)) -> Response:
    auth_service.logout(db, body.refresh_token)
    return Response(status_code=204)


@router.get("/me", response_model=MeResponse)
def me(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> MeResponse:
    user = users_repo.get_user_by_id(db, principal.user_id)
    assert user is not None
    return MeResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        platform_role=user.platform_role.value if user.platform_role else None,
        memberships=[
            MembershipOut(
                organization_id=m.organization_id,
                role=m.role,
                status=m.status,
            )
            for m in principal.memberships
        ],
    )
