import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.execution_log import ExecutionSource
from app.models.schedule import Schedule, ScheduleTargetType, ScheduleType
from app.repositories.group_repository import GroupRepository
from app.repositories.instance_repository import InstanceRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.db.session import SessionLocal
from app.services.audit_service import AuditService
from app.services.instance_service import InstanceService
from app.services.oci_cli import OCIService

logger = logging.getLogger(__name__)

class ScheduleService:
    def __init__(self, session: Session, instance_service: InstanceService) -> None:
        self.session = session
        self.instances = InstanceRepository(session)
        self.groups = GroupRepository(session)
        self.schedules = ScheduleRepository(session)
        self.instance_service = instance_service
        self.audit = AuditService(session)

    def list_schedules(self) -> list[Schedule]:
        return self.schedules.list()

    def get_schedule(self, schedule_id: str) -> Schedule:
        schedule = self.schedules.get(schedule_id)
        if schedule is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
        return schedule

    def create_schedule(self, payload: ScheduleCreate, *, actor_email: str | None = None, actor_user_id: str | None = None) -> Schedule:
        self._validate_target(payload.target_type, payload.instance_id, payload.group_id)
        schedule = self.schedules.create(payload)
        self.audit.log_configuration_event(
            event_type="schedule_created",
            entity_type="schedule",
            entity_id=schedule.id,
            actor_email=actor_email,
            actor_user_id=actor_user_id,
            summary=f"Schedule {schedule.id} created",
            after_data=self._serialize_schedule(schedule),
        )
        return schedule

    def update_schedule(self, schedule_id: str, payload: ScheduleUpdate, *, actor_email: str | None = None, actor_user_id: str | None = None) -> Schedule:
        schedule = self.get_schedule(schedule_id)
        before_data = self._serialize_schedule(schedule)
        next_target_type = payload.target_type or schedule.target_type
        next_instance_id = payload.instance_id if "instance_id" in payload.model_fields_set else schedule.instance_id
        next_group_id = payload.group_id if "group_id" in payload.model_fields_set else schedule.group_id
        self._validate_target(next_target_type, next_instance_id, next_group_id)
        schedule = self.schedules.update(schedule, payload)
        self.audit.log_configuration_event(
            event_type="schedule_updated",
            entity_type="schedule",
            entity_id=schedule.id,
            actor_email=actor_email,
            actor_user_id=actor_user_id,
            summary=f"Schedule {schedule.id} updated",
            before_data=before_data,
            after_data=self._serialize_schedule(schedule),
        )
        return schedule

    def delete_schedule(self, schedule_id: str, *, actor_email: str | None = None, actor_user_id: str | None = None) -> None:
        schedule = self.get_schedule(schedule_id)
        before_data = self._serialize_schedule(schedule)
        self.schedules.delete(schedule)
        self.audit.log_configuration_event(
            event_type="schedule_deleted",
            entity_type="schedule",
            entity_id=before_data["id"],
            actor_email=actor_email,
            actor_user_id=actor_user_id,
            summary=f"Schedule {before_data['id']} deleted",
            before_data=before_data,
        )

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
        if schedule.target_type == ScheduleTargetType.instance:
            instance = self.instances.get(schedule.instance_id) if schedule.instance_id else None
            if instance is None or not instance.enabled:
                return
            self._trigger_instance(schedule.action.value, instance.id, ExecutionSource.schedule)
        else:
            self._trigger_group(schedule)
        self.schedules.mark_triggered(schedule, now)

    def _validate_target(self, target_type: ScheduleTargetType, instance_id: str | None, group_id: str | None) -> None:
        if target_type == ScheduleTargetType.instance:
            if group_id is not None:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="group_id is not allowed for instance schedules")
            if not instance_id or self.instances.get(instance_id) is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
            return

        if instance_id is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="instance_id is not allowed for group schedules")
        if not group_id or self.groups.get(group_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    @staticmethod
    def _serialize_schedule(schedule: Schedule) -> dict:
        return {
            "id": schedule.id,
            "target_type": schedule.target_type.value,
            "instance_id": schedule.instance_id,
            "group_id": schedule.group_id,
            "type": schedule.type.value,
            "action": schedule.action.value,
            "run_at_utc": schedule.run_at_utc.isoformat() if schedule.run_at_utc else None,
            "days_of_week": list(schedule.days_of_week) if schedule.days_of_week else None,
            "time_utc": schedule.time_utc,
            "enabled": schedule.enabled,
            "last_triggered_at": schedule.last_triggered_at.isoformat() if schedule.last_triggered_at else None,
        }

    def _trigger_group(self, schedule: Schedule) -> None:
        if schedule.group_id is None:
            return
        group = self.groups.get(schedule.group_id)
        if group is None:
            return
        instance_ids = [instance.id for instance in group.instances if instance.enabled]
        if not instance_ids:
            return

        if not isinstance(self.instance_service, InstanceService):
            for instance_id in instance_ids:
                self._trigger_instance(schedule.action.value, instance_id, ExecutionSource.schedule)
            return

        max_concurrency = max(1, get_settings().schedule_group_max_concurrency)
        if max_concurrency == 1 or len(instance_ids) == 1:
            for instance_id in instance_ids:
                self._trigger_instance(schedule.action.value, instance_id, ExecutionSource.schedule)
            return

        worker_count = min(max_concurrency, len(instance_ids))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(self._trigger_instance_in_worker, schedule.action.value, instance_id) for instance_id in instance_ids]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    logger.exception("Group schedule member execution failed [schedule_id=%s group_id=%s]", schedule.id, schedule.group_id)

    def _trigger_instance(self, action: str, instance_id: str, source: ExecutionSource) -> None:
        if action == "start":
            self.instance_service.start(instance_id, source=source)
        elif action == "stop":
            self.instance_service.stop(instance_id, source=source)
        else:
            self.instance_service.restart(instance_id, source=source)

    @staticmethod
    def _trigger_instance_in_worker(action: str, instance_id: str) -> None:
        with SessionLocal() as session:
            instance_service = InstanceService(session, OCIService())
            if action == "start":
                instance_service.start(instance_id, source=ExecutionSource.schedule)
            elif action == "stop":
                instance_service.stop(instance_id, source=ExecutionSource.schedule)
            else:
                instance_service.restart(instance_id, source=ExecutionSource.schedule)

    @staticmethod
    def _ensure_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
