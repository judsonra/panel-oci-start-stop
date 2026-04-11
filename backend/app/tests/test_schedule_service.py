from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from app.api.routes import list_schedules
from app.core.config import Settings
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


class FakeFuture:
    def result(self):
        return None


class FakeThreadPoolExecutor:
    def __init__(self, *, max_workers: int) -> None:
        self.max_workers = max_workers
        self.submitted = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, *args):
        self.submitted.append((fn, args))
        return FakeFuture()


def test_settings_default_group_max_concurrency_is_10(monkeypatch):
    monkeypatch.delenv("SCHEDULE_GROUP_MAX_CONCURRENCY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.schedule_group_max_concurrency == 10


def test_settings_env_overrides_group_max_concurrency(monkeypatch):
    monkeypatch.setenv("SCHEDULE_GROUP_MAX_CONCURRENCY", "7")

    settings = Settings(_env_file=None)

    assert settings.schedule_group_max_concurrency == 7


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


def test_is_due_weekly_prevents_duplicate_same_minute(override_session):
    instance = Instance(name="VM", ocid="ocid1.instance.oc1.sa-saopaulo-1.schedule2", enabled=True)
    override_session.add(instance)
    override_session.commit()
    override_session.refresh(instance)
    now = datetime(2026, 3, 10, 14, 30, tzinfo=timezone.utc)
    schedule = Schedule(
        target_type=ScheduleTargetType.instance,
        instance_id=instance.id,
        type=ScheduleType.weekly,
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
        type=ScheduleType.weekly,
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
        type=ScheduleType.weekly,
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
        type=ScheduleType.weekly,
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


def test_trigger_group_uses_instance_count_when_below_max_concurrency(override_session):
    instances = [
        Instance(name=f"VM {idx}", ocid=f"ocid1.instance.oc1.sa-saopaulo-1.schedule-below-{idx}", enabled=True)
        for idx in range(3)
    ]
    group = Group(name="Grupo Concorrencia Baixa", normalized_name="grupo concorrencia baixa")
    group.instances = instances
    override_session.add_all([*instances, group])
    override_session.commit()
    override_session.refresh(group)
    schedule = Schedule(
        target_type=ScheduleTargetType.group,
        group_id=group.id,
        type=ScheduleType.weekly,
        action=ScheduleAction.start,
        days_of_week=[1],
        time_utc="08:00",
        enabled=True,
    )
    service = ScheduleService(override_session, StubInstanceService())  # type: ignore[arg-type]
    executor_calls = []

    def build_executor(*, max_workers: int):
        executor = FakeThreadPoolExecutor(max_workers=max_workers)
        executor_calls.append(executor)
        return executor

    with patch("app.services.schedule_service.get_settings", return_value=SimpleNamespace(schedule_group_max_concurrency=10)):
        with patch("app.services.schedule_service.ThreadPoolExecutor", side_effect=build_executor):
            with patch("app.services.schedule_service.as_completed", side_effect=lambda futures: futures):
                service._trigger_group(schedule)

    assert len(executor_calls) == 1
    assert executor_calls[0].max_workers == 3
    assert len(executor_calls[0].submitted) == 3


def test_trigger_group_limits_thread_pool_to_10_workers(override_session):
    instances = [
        Instance(name=f"VM {idx}", ocid=f"ocid1.instance.oc1.sa-saopaulo-1.schedule-cap-{idx}", enabled=True)
        for idx in range(12)
    ]
    group = Group(name="Grupo Concorrencia Alta", normalized_name="grupo concorrencia alta")
    group.instances = instances
    override_session.add_all([*instances, group])
    override_session.commit()
    override_session.refresh(group)
    schedule = Schedule(
        target_type=ScheduleTargetType.group,
        group_id=group.id,
        type=ScheduleType.weekly,
        action=ScheduleAction.stop,
        days_of_week=[1],
        time_utc="08:00",
        enabled=True,
    )
    service = ScheduleService(override_session, StubInstanceService())  # type: ignore[arg-type]
    executor_calls = []

    def build_executor(*, max_workers: int):
        executor = FakeThreadPoolExecutor(max_workers=max_workers)
        executor_calls.append(executor)
        return executor

    with patch("app.services.schedule_service.get_settings", return_value=SimpleNamespace(schedule_group_max_concurrency=10)):
        with patch("app.services.schedule_service.ThreadPoolExecutor", side_effect=build_executor):
            with patch("app.services.schedule_service.as_completed", side_effect=lambda futures: futures):
                service._trigger_group(schedule)

    assert len(executor_calls) == 1
    assert executor_calls[0].max_workers == 10
    assert len(executor_calls[0].submitted) == 12


def test_is_due_monthly_schedule(override_session):
    instance = Instance(name="VM", ocid="ocid1.instance.oc1.sa-saopaulo-1.schedule9", enabled=True)
    override_session.add(instance)
    override_session.commit()
    override_session.refresh(instance)
    now = datetime(2026, 4, 15, 9, 45, tzinfo=timezone.utc)
    schedule = Schedule(
        target_type=ScheduleTargetType.instance,
        instance_id=instance.id,
        type=ScheduleType.monthly,
        action=ScheduleAction.start,
        days_of_month=[1, 15, 30],
        time_utc="09:45",
        enabled=True,
    )
    override_session.add(schedule)
    override_session.commit()
    stub = StubInstanceService()
    service = ScheduleService(override_session, stub)  # type: ignore[arg-type]

    assert service.is_due(schedule, now) is True


def test_is_due_monthly_schedule_skips_missing_day(override_session):
    instance = Instance(name="VM", ocid="ocid1.instance.oc1.sa-saopaulo-1.schedule10", enabled=True)
    override_session.add(instance)
    override_session.commit()
    override_session.refresh(instance)
    now = datetime(2026, 4, 30, 9, 45, tzinfo=timezone.utc)
    schedule = Schedule(
        target_type=ScheduleTargetType.instance,
        instance_id=instance.id,
        type=ScheduleType.monthly,
        action=ScheduleAction.start,
        days_of_month=[31],
        time_utc="09:45",
        enabled=True,
    )
    override_session.add(schedule)
    override_session.commit()
    stub = StubInstanceService()
    service = ScheduleService(override_session, stub)  # type: ignore[arg-type]

    assert service.is_due(schedule, now) is False


def test_process_due_monthly_schedule_triggers_restart(override_session):
    instance = Instance(name="VM", ocid="ocid1.instance.oc1.sa-saopaulo-1.schedule11", enabled=True)
    override_session.add(instance)
    override_session.commit()
    override_session.refresh(instance)
    now = datetime(2026, 4, 20, 11, 5, tzinfo=timezone.utc)
    schedule = Schedule(
        target_type=ScheduleTargetType.instance,
        instance_id=instance.id,
        type=ScheduleType.monthly,
        action=ScheduleAction.restart,
        days_of_month=[20],
        time_utc="11:05",
        enabled=True,
    )
    override_session.add(schedule)
    override_session.commit()
    stub = StubInstanceService()
    service = ScheduleService(override_session, stub)  # type: ignore[arg-type]

    assert service.process_due_schedules(now) == 1
    assert stub.called == [("restart", instance.id, ExecutionSource.schedule)]
