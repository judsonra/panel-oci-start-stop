from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.execution_log import ExecutionLog


class ExecutionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, limit: int = 50) -> list[ExecutionLog]:
        statement = select(ExecutionLog).options(joinedload(ExecutionLog.instance)).order_by(ExecutionLog.started_at.desc()).limit(limit)
        return list(self.session.scalars(statement).all())

    def create(self, execution_log: ExecutionLog) -> ExecutionLog:
        self.session.add(execution_log)
        self.session.commit()
        self.session.refresh(execution_log)
        return execution_log

    def update(self, execution_log: ExecutionLog) -> ExecutionLog:
        self.session.add(execution_log)
        self.session.commit()
        self.session.refresh(execution_log)
        return execution_log
