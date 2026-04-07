from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditAccessLog, AuditConfigurationLog


class AuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def log_access_event(
        self,
        *,
        event_type: str,
        auth_source: str | None = None,
        email: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        path: str | None = None,
        method: str | None = None,
        status_code: int | None = None,
        message: str | None = None,
    ) -> AuditAccessLog:
        log = AuditAccessLog(
            event_type=event_type,
            auth_source=auth_source,
            email=email,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            path=path,
            method=method,
            status_code=status_code,
            message=message,
        )
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def log_configuration_event(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str | None,
        actor_email: str | None,
        actor_user_id: str | None,
        summary: str,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
    ) -> AuditConfigurationLog:
        log = AuditConfigurationLog(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_email=actor_email,
            actor_user_id=actor_user_id,
            summary=summary,
            before_data=before_data,
            after_data=after_data,
        )
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def list_access_logs(
        self,
        *,
        email: str | None = None,
        event_type: str | None = None,
        auth_source: str | None = None,
        query: str | None = None,
    ) -> list[AuditAccessLog]:
        statement = select(AuditAccessLog)
        if email:
            statement = statement.where(AuditAccessLog.email == email)
        if event_type:
            statement = statement.where(AuditAccessLog.event_type == event_type)
        if auth_source:
            statement = statement.where(AuditAccessLog.auth_source == auth_source)
        if query:
            like = f"%{query.strip()}%"
            statement = statement.where(
                or_(AuditAccessLog.path.ilike(like), AuditAccessLog.message.ilike(like), AuditAccessLog.email.ilike(like))
            )
        statement = statement.order_by(AuditAccessLog.created_at.desc())
        return list(self.session.scalars(statement).all())

    def list_configuration_logs(
        self,
        *,
        actor_email: str | None = None,
        event_type: str | None = None,
        entity_type: str | None = None,
        query: str | None = None,
    ) -> list[AuditConfigurationLog]:
        statement = select(AuditConfigurationLog)
        if actor_email:
            statement = statement.where(AuditConfigurationLog.actor_email == actor_email)
        if event_type:
            statement = statement.where(AuditConfigurationLog.event_type == event_type)
        if entity_type:
            statement = statement.where(AuditConfigurationLog.entity_type == entity_type)
        if query:
            like = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    AuditConfigurationLog.summary.ilike(like),
                    AuditConfigurationLog.entity_type.ilike(like),
                    AuditConfigurationLog.actor_email.ilike(like),
                )
            )
        statement = statement.order_by(AuditConfigurationLog.created_at.desc())
        return list(self.session.scalars(statement).all())
