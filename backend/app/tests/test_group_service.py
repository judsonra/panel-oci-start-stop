from fastapi import HTTPException

from app.services.compartment_service import CompartmentService
from app.services.group_service import GroupService
from app.services.instance_service import InstanceService
from app.schemas.instance import InstanceCreate
from app.models.schedule import Schedule, ScheduleAction, ScheduleTargetType, ScheduleType
from app.repositories.group_repository import GroupRepository
from app.tests.conftest import fake_oci_service
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def test_group_service_creates_group_and_keeps_instances_sorted(override_session):
    CompartmentService(override_session, fake_oci_service).list_and_update()
    instance_service = InstanceService(override_session, fake_oci_service)
    imported = instance_service.import_all_compartment_instances()
    assert imported.created == 2

    instances = sorted(instance_service.list_instances(), key=lambda item: item.name)
    service = GroupService(override_session)

    group = service.create_group("Operação A", [instances[1].id, instances[0].id])

    assert group.name == "Operação A"
    assert [item.name for item in group.instances] == ["Instance A1", "Instance B1"]


def test_group_service_rejects_duplicate_normalized_name(override_session):
    compartments = CompartmentService(override_session, fake_oci_service).list_and_update()
    instance_service = InstanceService(override_session, fake_oci_service)
    created = instance_service.create_instance(
        InstanceCreate(
            name="VM Manual",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.manualgroup",
            compartment_id=compartments[0].id,
            description=None,
            enabled=True,
        )
    )
    service = GroupService(override_session)
    service.create_group("Grupo Banco", [created.id])

    try:
        service.create_group("  grupo   banco ", [created.id])
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Expected duplicate group name to raise HTTPException")


def test_group_service_lists_tree_by_compartment(override_session):
    CompartmentService(override_session, fake_oci_service).list_and_update()
    instance_service = InstanceService(override_session, fake_oci_service)
    instance_service.import_all_compartment_instances()
    service = GroupService(override_session)

    tree = service.list_tree()

    assert [compartment.name for compartment in tree] == ["Compartment A", "Compartment B"]
    assert [instance.name for instance in tree[0].instances] == ["Instance A1"]


def test_group_service_deletes_group_when_no_linked_schedule(override_session):
    service = GroupService(override_session)
    group = service.create_group("Grupo Sem Agenda", [])

    service.delete_group(group.id)

    assert service.groups.get(group.id) is None


def test_group_service_blocks_delete_when_group_has_active_schedule(override_session):
    service = GroupService(override_session)
    group = service.create_group("Grupo Com Agenda Ativa", [])
    schedule = Schedule(
        target_type=ScheduleTargetType.group,
        group_id=group.id,
        type=ScheduleType.weekly,
        action=ScheduleAction.start,
        days_of_week=[0],
        time_utc="10:00",
        enabled=True,
    )
    override_session.add(schedule)
    override_session.commit()

    try:
        service.delete_group(group.id)
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "Group is linked to one or more schedules"
    else:
        raise AssertionError("Expected linked active schedule to block group deletion")

    assert service.groups.get(group.id) is not None


def test_group_service_blocks_delete_when_group_has_inactive_schedule(override_session):
    service = GroupService(override_session)
    group = service.create_group("Grupo Com Agenda Inativa", [])
    schedule = Schedule(
        target_type=ScheduleTargetType.group,
        group_id=group.id,
        type=ScheduleType.weekly,
        action=ScheduleAction.stop,
        days_of_week=[1],
        time_utc="11:00",
        enabled=False,
    )
    override_session.add(schedule)
    override_session.commit()

    try:
        service.delete_group(group.id)
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "Group is linked to one or more schedules"
    else:
        raise AssertionError("Expected linked inactive schedule to block group deletion")

    assert service.groups.get(group.id) is not None


def test_group_repository_delete_fails_with_fk_restriction_when_schedule_exists(override_session):
    # SQLite requires this pragma enabled per connection for FK enforcement.
    override_session.execute(text("PRAGMA foreign_keys=ON"))
    service = GroupService(override_session)
    group = service.create_group("Grupo FK Restrict", [])
    schedule = Schedule(
        target_type=ScheduleTargetType.group,
        group_id=group.id,
        type=ScheduleType.weekly,
        action=ScheduleAction.restart,
        days_of_week=[2],
        time_utc="12:00",
        enabled=False,
    )
    override_session.add(schedule)
    override_session.commit()

    try:
        GroupRepository(override_session).delete(group)
    except IntegrityError:
        override_session.rollback()
    else:
        raise AssertionError("Expected FK restriction to block direct repository delete")
