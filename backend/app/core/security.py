from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from sqlalchemy.orm import Session


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    subject: str
    email: str | None
    groups: list[str]
    permissions: list[str]
    auth_source: str
    is_superadmin: bool
    access_user_id: str | None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_db_session),
) -> CurrentUser:
    if not settings.auth_enabled and not settings.entra_auth_enabled and not settings.local_admin_enabled:
        current_user = CurrentUser(
            subject="local-dev",
            email="local@example.com",
            groups=["local"],
            permissions=["*"],
            auth_source="local-dev",
            is_superadmin=True,
            access_user_id=None,
        )
        request.state.current_user = current_user
        return current_user
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    from app.services.auth_service import AuthService

    auth_service = AuthService(session, settings)
    current_user = auth_service.authenticate_app_token(credentials.credentials)
    request.state.current_user = current_user
    return current_user


def require_permission(permission_key: str) -> Callable[[CurrentUser], CurrentUser]:
    def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.is_superadmin or "*" in current_user.permissions or permission_key in current_user.permissions:
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    return dependency


def require_any_permission(*permission_keys: str) -> Callable[[CurrentUser], CurrentUser]:
    def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.is_superadmin or "*" in current_user.permissions:
            return current_user
        if any(permission in current_user.permissions for permission in permission_keys):
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    return dependency


def require_superadmin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.is_superadmin:
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin required")
