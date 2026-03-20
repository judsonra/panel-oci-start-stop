from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.execution_log import ExecutionSource
from app.models.schedule import Schedule, ScheduleType
from app.repositories.instance_repository import InstanceRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.services.instance_service import InstanceService


class ScheduleService:
    def __init__(self, session: Session, instance_service: InstanceService) -> None:
        self.session = session
        self.instances = InstanceRepository(session)
        self.schedules = ScheduleRepository(session)
        self.instance_service = instance_service

    def list_schedules(self) -> list[Schedule]:
        return self.schedules.list()

    def get_schedule(self, schedule_id: str) -> Schedule:
        schedule = self.schedules.get(schedule_id)
        if schedule is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
        return schedule

    def create_schedule(self, payload: ScheduleCreate) -> Schedule:
        if self.instances.get(payload.instance_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
        return self.schedules.create(payload)

    def update_schedule(self, schedule_id: str, payload: ScheduleUpdate) -> Schedule:
        schedule = self.get_schedule(schedule_id)
        if payload.instance_id is not None and self.instances.get(payload.instance_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
        return self.schedules.update(schedule, payload)

    def delete_schedule(self, schedule_id: str) -> None:
        schedule = self.get_schedule(schedule_id)
        self.schedules.delete(schedule)

    def process_due_schedules(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        triggered = 0
        for schedule in self.schedules.list_due(now):
            if self.is_due(schedule, now):
                self.trigger(schedule, now)
                triggered += 1
        return triggered

    def is_due(self, schedule: Schedule, now: datetime) -> bool:
        now = self._ensure_utc(now)
        if not schedule.enabled:
            return False
        if schedule.type == ScheduleType.one_time:
            run_at_utc = self._ensure_utc(schedule.run_at_utc)
            if run_at_utc is None or run_at_utc > now:
                return False
            if schedule.last_triggered_at is not None:
                return False
            return True
        if schedule.days_of_week is None or schedule.time_utc is None:
            return False
        hour, minute = [int(part) for part in schedule.time_utc.split(":")]
        current_slot = now.replace(second=0, microsecond=0)
        if now.weekday() not in schedule.days_of_week:
            return False
        if now.hour != hour or now.minute != minute:
            return False
        last_triggered_at = self._ensure_utc(schedule.last_triggered_at)
        if last_triggered_at is not None and last_triggered_at >= current_slot:
            return False
        return True

    def trigger(self, schedule: Schedule, now: datetime) -> None:
        instance = self.instances.get(schedule.instance_id)
        if instance is None or not instance.enabled:
            return
        if schedule.action.value == "start":
            self.instance_service.start(instance.id, source=ExecutionSource.schedule)
        elif schedule.action.value == "stop":
            self.instance_service.stop(instance.id, source=ExecutionSource.schedule)
        else:
            self.instance_service.restart(instance.id, source=ExecutionSource.schedule)
        self.schedules.mark_triggered(schedule, now)

    @staticmethod
    def _ensure_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
