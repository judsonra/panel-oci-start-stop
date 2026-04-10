import asyncio
from datetime import datetime, timezone

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.api.audit_middleware import AuditAccessMiddleware
from app.core.security import CurrentUser
from app.models.audit_log import AuditAccessLog
from app.schemas.audit import AuditAccessLogRead
from app.services.audit_service import AuditService


class SessionContext:
    def __init__(self, session) -> None:
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


def build_request(path: str) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [(b"user-agent", b"pytest-agent")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_audit_middleware_logs_request_duration(monkeypatch, override_session):
    monkeypatch.setattr("app.api.audit_middleware.SessionLocal", lambda: SessionContext(override_session))
    middleware = AuditAccessMiddleware(app=lambda scope, receive, send: None)
    request = build_request("/api/instances")

    async def call_next(current_request: Request) -> Response:
        current_request.state.current_user = CurrentUser(
            subject="local-dev",
            email="local@example.com",
            groups=["local"],
            permissions=["*"],
            auth_source="local-dev",
            is_superadmin=True,
            access_user_id=None,
        )
        return Response(status_code=200)

    response = asyncio.run(middleware.dispatch(request, call_next))

    log = override_session.query(AuditAccessLog).one()
    assert response.status_code == 200
    assert log.event_type == "api_access"
    assert log.path == "/api/instances"
    assert log.status_code == 200
    assert log.email == "local@example.com"
    assert log.started_at is not None
    assert log.finished_at is not None
    assert log.duration_ms is not None
    assert log.duration_ms >= 0
    assert log.finished_at >= log.started_at


def test_audit_middleware_logs_access_denied(monkeypatch, override_session):
    monkeypatch.setattr("app.api.audit_middleware.SessionLocal", lambda: SessionContext(override_session))
    middleware = AuditAccessMiddleware(app=lambda scope, receive, send: None)
    request = build_request("/api/admin/users")

    async def call_next(_: Request) -> Response:
        return Response(status_code=403)

    asyncio.run(middleware.dispatch(request, call_next))

    log = override_session.query(AuditAccessLog).one()
    assert log.event_type == "access_denied"
    assert log.status_code == 403
    assert log.started_at is not None
    assert log.finished_at is not None
    assert log.duration_ms is not None


def test_audit_middleware_logs_internal_server_error(monkeypatch, override_session):
    monkeypatch.setattr("app.api.audit_middleware.SessionLocal", lambda: SessionContext(override_session))
    middleware = AuditAccessMiddleware(app=lambda scope, receive, send: None)
    request = build_request("/api/instances/status-refresh")

    async def call_next(_: Request) -> Response:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(middleware.dispatch(request, call_next))

    log = override_session.query(AuditAccessLog).one()
    assert log.event_type == "api_access"
    assert log.status_code == 500
    assert log.started_at is not None
    assert log.finished_at is not None
    assert log.duration_ms is not None


def test_audit_access_schema_includes_timing_fields(override_session):
    started_at = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
    finished_at = datetime(2026, 4, 10, 12, 0, 1, tzinfo=timezone.utc)
    created = AuditService(override_session).log_access_event(
        event_type="api_access",
        path="/api/schedules",
        method="GET",
        status_code=200,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=1000,
    )

    payload = AuditAccessLogRead.model_validate(created)

    assert payload.started_at == started_at
    assert payload.finished_at == finished_at
    assert payload.duration_ms == 1000
