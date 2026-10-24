from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.principal import MembershipInfo, Principal
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import UserStatus
from app.repositories import users as users_repo

_bearer = HTTPBearer(auto_error=False)


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        user_id = decode_access_token(credentials.credentials)
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        ) from None

    user = users_repo.get_user_by_id(db, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    memberships = users_repo.list_active_memberships(db, user.id)
    return Principal(
        user_id=user.id,
        platform_role=user.platform_role.value if user.platform_role else None,
        memberships=[
            MembershipInfo(
                organization_id=m.organization_id,
                role=m.role.value,
                status=m.status.value,
            )
            for m in memberships
        ],
        team_ids=[],
    )
