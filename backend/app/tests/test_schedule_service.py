from datetime import datetime, timedelta, timezone

from app.api.routes import list_schedules
from app.core.security import CurrentUser
from app.models.execution_log import ExecutionSource
from app.models.group import Group
from app.models.instance import Instance
from app.models.schedule import Schedule, ScheduleAction, ScheduleTargetType, ScheduleType
from app.services.schedule_service import ScheduleService


class StubInstanceService:
    def __init__(self) -> None:
        self.called = []

    def start(self, instance_id: str, source):
        self.called.append(("start", instance_id, source))

    def stop(self, instance_id: str, source):
        self.called.append(("stop", instance_id, source))

    def restart(self, instance_id: str, source):
        self.called.append(("restart", instance_id, source))


def test_is_due_one_time_schedule(override_session):
    instance = Instance(name="VM", ocid="ocid1.instance.oc1.sa-saopaulo-1.schedule1", enabled=True)
    override_session.add(instance)
    override_session.commit()
    override_session.refresh(instance)
    schedule = Schedule(
        target_type=ScheduleTargetType.instance,
        instance_id=instance.id,
        type=ScheduleType.one_time,
        action=ScheduleAction.start,
        run_at_utc=datetime.now(timezone.utc) - timedelta(minutes=1),
        enabled=True,
    )
    override_session.add(schedule)
    override_session.commit()
    stub = StubInstanceService()
    service = ScheduleService(override_session, stub)  # type: ignore[arg-type]
    assert service.is_due(schedule, datetime.now(timezone.utc)) is True


def test_is_due_recurring_prevents_duplicate_same_minute(override_session):
    instance = Instance(name="VM", ocid="ocid1.instance.oc1.sa-saopaulo-1.schedule2", enabled=True)
    override_session.add(instance)
    override_session.commit()
    override_session.refresh(instance)
    now = datetime(2026, 3, 10, 14, 30, tzinfo=timezone.utc)
    schedule = Schedule(
        target_type=ScheduleTargetType.instance,
        instance_id=instance.id,
        type=ScheduleType.recurring,
        action=ScheduleAction.stop,
        days_of_week=[now.weekday()],
        time_utc="14:30",
        enabled=True,
        last_triggered_at=now.replace(second=0, microsecond=0),
    )
    override_session.add(schedule)
    override_session.commit()
    stub = StubInstanceService()
    service = ScheduleService(override_session, stub)  # type: ignore[arg-type]
    assert service.is_due(schedule, now) is False


def test_process_due_schedules_skips_cli_when_instance_disabled(override_session):
    instance = Instance(name="VM", ocid="ocid1.instance.oc1.sa-saopaulo-1.schedule3", enabled=False)
    override_session.add(instance)
    override_session.commit()
    override_session.refresh(instance)
    schedule = Schedule(
        target_type=ScheduleTargetType.instance,
        instance_id=instance.id,
        type=ScheduleType.one_time,
        action=ScheduleAction.start,
        run_at_utc=datetime.now(timezone.utc) - timedelta(minutes=1),
        enabled=True,
    )
    override_session.add(schedule)
    override_session.commit()
    stub = StubInstanceService()
    service = ScheduleService(override_session, stub)  # type: ignore[arg-type]
    assert service.process_due_schedules(datetime.now(timezone.utc)) == 1
    assert stub.called == []


def test_list_schedules_route_returns_instance_name(override_session):
    instance = Instance(name="VM Nome", ocid="ocid1.instance.oc1.sa-saopaulo-1.schedule4", enabled=True)
    override_session.add(instance)
    override_session.commit()
    override_session.refresh(instance)
    schedule = Schedule(
        target_type=ScheduleTargetType.instance,
        instance_id=instance.id,
        type=ScheduleType.recurring,
        action=ScheduleAction.start,
        days_of_week=[1, 2, 3],
        time_utc="14:30",
        enabled=True,
    )
    override_session.add(schedule)
    override_session.commit()
    stub = StubInstanceService()
    service = ScheduleService(override_session, stub)  # type: ignore[arg-type]

    response = list_schedules(CurrentUser(subject="local", email=None, groups=[]), service)

    assert len(response) == 1
    assert response[0].target_type == ScheduleTargetType.instance
    assert response[0].instance_id == instance.id
    assert response[0].instance_name == "VM Nome"


def test_process_due_schedules_triggers_restart(override_session):
    instance = Instance(name="VM", ocid="ocid1.instance.oc1.sa-saopaulo-1.schedule5", enabled=True)
    override_session.add(instance)
    override_session.commit()
    override_session.refresh(instance)
    now = datetime(2026, 3, 12, 10, 15, tzinfo=timezone.utc)
    schedule = Schedule(
        target_type=ScheduleTargetType.instance,
        instance_id=instance.id,
        type=ScheduleType.recurring,
        action=ScheduleAction.restart,
        days_of_week=[now.weekday()],
        time_utc="10:15",
        enabled=True,
    )
    override_session.add(schedule)
    override_session.commit()
    stub = StubInstanceService()
    service = ScheduleService(override_session, stub)  # type: ignore[arg-type]

    assert service.process_due_schedules(now) == 1
    assert stub.called == [("restart", instance.id, ExecutionSource.schedule)]


def test_process_due_group_schedule_triggers_all_enabled_instances(override_session):
    instance_a = Instance(name="VM A", ocid="ocid1.instance.oc1.sa-saopaulo-1.schedule6", enabled=True)
    instance_b = Instance(name="VM B", ocid="ocid1.instance.oc1.sa-saopaulo-1.schedule7", enabled=True)
    instance_c = Instance(name="VM C", ocid="ocid1.instance.oc1.sa-saopaulo-1.schedule8", enabled=False)
    group = Group(name="Grupo Teste", normalized_name="grupo teste")
    group.instances = [instance_a, instance_b, instance_c]
    override_session.add_all([instance_a, instance_b, instance_c, group])
    override_session.commit()
    override_session.refresh(group)
    now = datetime(2026, 3, 12, 10, 15, tzinfo=timezone.utc)
    schedule = Schedule(
        target_type=ScheduleTargetType.group,
        group_id=group.id,
        type=ScheduleType.recurring,
        action=ScheduleAction.stop,
        days_of_week=[now.weekday()],
        time_utc="10:15",
        enabled=True,
    )
    override_session.add(schedule)
    override_session.commit()
    stub = StubInstanceService()
    service = ScheduleService(override_session, stub)  # type: ignore[arg-type]

    assert service.process_due_schedules(now) == 1
    assert stub.called == [
        ("stop", instance_a.id, ExecutionSource.schedule),
        ("stop", instance_b.id, ExecutionSource.schedule),
    ]
