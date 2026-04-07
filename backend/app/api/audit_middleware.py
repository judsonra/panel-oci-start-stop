from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.audit_service import AuditService


class AuditAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/api") or request.url.path in {"/api/health", "/api/auth/config"}:
            return response

        settings = get_settings()
        if not (settings.entra_auth_enabled or settings.local_admin_enabled or settings.auth_enabled):
            return response

        current_user = getattr(request.state, "current_user", None)
        event_type = "api_access"
        if response.status_code in {401, 403}:
            event_type = "access_denied"

        with SessionLocal() as session:
            AuditService(session).log_access_event(
                event_type=event_type,
                auth_source=getattr(current_user, "auth_source", None),
                email=getattr(current_user, "email", None),
                user_id=getattr(current_user, "access_user_id", None),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                message=None,
            )
        return response
