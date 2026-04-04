from fastapi import HTTPException

from app.services.compartment_service import CompartmentService
from app.services.group_service import GroupService
from app.services.instance_service import InstanceService
from app.schemas.instance import InstanceCreate
from app.tests.conftest import fake_oci_service


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
