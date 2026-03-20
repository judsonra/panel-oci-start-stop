from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.schedule import Schedule, ScheduleType
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate


class ScheduleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Schedule]:
        statement = select(Schedule).options(joinedload(Schedule.instance)).order_by(Schedule.created_at.desc())
        return list(self.session.scalars(statement).all())

    def get(self, schedule_id: str) -> Schedule | None:
        return self.session.get(Schedule, schedule_id)

    def list_due(self, now: datetime) -> list[Schedule]:
        statement = select(Schedule).where(Schedule.enabled.is_(True))
        return list(self.session.scalars(statement).all())

    def create(self, payload: ScheduleCreate) -> Schedule:
        schedule = Schedule(**payload.model_dump())
        self.session.add(schedule)
        self.session.commit()
        self.session.refresh(schedule)
        return schedule

    def update(self, schedule: Schedule, payload: ScheduleUpdate) -> Schedule:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(schedule, field, value)
        self.session.add(schedule)
        self.session.commit()
        self.session.refresh(schedule)
        return schedule

    def mark_triggered(self, schedule: Schedule, triggered_at: datetime) -> Schedule:
        schedule.last_triggered_at = triggered_at
        if schedule.type == ScheduleType.one_time:
            schedule.enabled = False
        self.session.add(schedule)
        self.session.commit()
        self.session.refresh(schedule)
        return schedule

    def delete(self, schedule: Schedule) -> None:
        self.session.delete(schedule)
        self.session.commit()
