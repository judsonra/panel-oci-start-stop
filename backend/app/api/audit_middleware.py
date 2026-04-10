from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.db.session import SessionLocal
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AuditAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api") or request.url.path in {"/api/health", "/api/auth/config"}:
            return await call_next(request)

        started_at = datetime.now(timezone.utc)
        started_perf = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            self._log_request(request, status_code=500, started_at=started_at, started_perf=started_perf)
            raise

        self._log_request(request, status_code=response.status_code, started_at=started_at, started_perf=started_perf)
        return response

    @staticmethod
    def _log_request(request: Request, *, status_code: int, started_at: datetime, started_perf: float) -> None:
        finished_at = datetime.now(timezone.utc)
        duration_ms = max(0, int((time.perf_counter() - started_perf) * 1000))
        current_user = getattr(request.state, "current_user", None)
        event_type = "api_access"
        if status_code in {401, 403}:
            event_type = "access_denied"
        try:
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
                    status_code=status_code,
                    message=None,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                )
        except Exception:
            logger.exception("Failed to persist audit access log [path=%s method=%s]", request.url.path, request.method)
