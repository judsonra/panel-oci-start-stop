from __future__ import annotations

from datetime import datetime

from app.schemas.common import AppBaseModel


class AuditAccessLogRead(AppBaseModel):
    id: str
    event_type: str
    auth_source: str | None = None
    email: str | None = None
    user_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    path: str | None = None
    method: str | None = None
    status_code: int | None = None
    message: str | None = None
    created_at: datetime


class AuditConfigurationLogRead(AppBaseModel):
    id: str
    event_type: str
    entity_type: str
    entity_id: str | None = None
    actor_email: str | None = None
    actor_user_id: str | None = None
    summary: str
    before_data: dict | None = None
    after_data: dict | None = None
    created_at: datetime
