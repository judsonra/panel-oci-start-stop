from fastapi import HTTPException

from app.api.routes import (
    create_instance,
    get_instance_import_preview,
    get_instance_vnic,
    get_status,
    get_vnic_details,
    import_all_compartment_instances,
    import_instance,
)
from app.core.security import CurrentUser
from app.models.execution_log import ExecutionStatus
from app.schemas.instance import InstanceCreate, InstanceImportCreate
from app.services.compartment_service import CompartmentService
from app.services.instance_service import InstanceService
from app.tests.conftest import fake_oci_service


def test_create_instance_success(override_session):
    service = InstanceService(override_session, fake_oci_service)
    payload = InstanceCreate(
        name="VM Principal",
        ocid="ocid1.instance.oc1.sa-saopaulo-1.anyvalidvalue",
        description="instancia de teste",
        enabled=True,
    )
    created = service.create_instance(payload)
    assert created.name == "VM Principal"
    assert created.last_known_state is None


def test_create_instance_route_serializes_response(override_session):
    service = InstanceService(override_session, fake_oci_service)
    payload = InstanceCreate(
        name="VM API",
        ocid="ocid1.instance.oc1.sa-saopaulo-1.routesample",
        description="instancia via route",
        enabled=True,
    )
    response = create_instance(payload, CurrentUser(subject="local", email=None, groups=[]), service)
    assert response.name == "VM API"
    assert response.ocid == "ocid1.instance.oc1.sa-saopaulo-1.routesample"


def test_create_instance_rejects_duplicate_ocid(override_session):
    service = InstanceService(override_session, fake_oci_service)
    payload = InstanceCreate(
        name="VM Principal",
        ocid="ocid1.instance.oc1.sa-saopaulo-1.duplicate",
        description="instancia de teste",
        enabled=True,
    )
    service.create_instance(payload)
    try:
        service.create_instance(payload)
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Expected duplicate OCID to raise HTTPException")


def test_start_instance_creates_success_log(override_session):
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="VM Start",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.startable",
            description="instancia de teste",
            enabled=True,
        )
    )
    execution = service.start(created.id)
    assert execution.status == ExecutionStatus.success
    assert execution.stdout_summary == "started"


def test_start_instance_creates_failure_log(override_session):
    service = InstanceService(override_session, fake_oci_service)
    fake_oci_service.mode = "failure"
    created = service.create_instance(
        InstanceCreate(
            name="VM Fail",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.failcase",
            description="instancia de teste",
            enabled=True,
        )
    )
    execution = service.start(created.id)
    assert execution.status == ExecutionStatus.failed
    assert execution.stderr_summary == "oci_command_failed"


def test_start_instance_rejects_disabled_instance(override_session):
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="VM Disabled",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.disabled",
            description="instancia desabilitada",
            enabled=False,
        )
    )
    try:
        service.start(created.id)
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("Expected disabled instance to raise HTTPException")


def test_get_status_route_returns_instance_state(override_session):
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="VM Status",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.statuscheck",
            description="instancia de teste",
            enabled=True,
        )
    )

    response = get_status(created.id, CurrentUser(subject="local", email=None, groups=[]), service)

    assert response.instance_id == created.id
    assert response.instance_state == "RUNNING"
    assert response.status == ExecutionStatus.success


def test_get_import_preview_returns_oci_fields_and_registration_flag(override_session):
    CompartmentService(override_session, fake_oci_service).list_and_update()
    service = InstanceService(override_session, fake_oci_service)

    response = get_instance_import_preview(
        "ocid1.instance.oc1.sa-saopaulo-1.autoa1",
        CurrentUser(subject="local", email=None, groups=[]),
        service,
    )

    assert response.name == "Instance A1"
    assert response.ocid == "ocid1.instance.oc1.sa-saopaulo-1.autoa1"
    assert response.compartment_ocid == "ocid1.compartment.oc1..aaaa"
    assert response.compartment_name == "Compartment A"
    assert response.vcpu == 2.0
    assert response.public_ip == "129.1.1.1"
    assert response.private_ip == "10.0.0.10"
    assert response.already_registered is False


def test_get_import_preview_marks_existing_instance_as_already_registered(override_session):
    CompartmentService(override_session, fake_oci_service).list_and_update()
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="Instance A1",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
            description="existente",
            enabled=True,
        )
    )
    service.instances.apply_updates(
        created,
        {
            "compartment_id": service.compartments.get_by_ocid("ocid1.compartment.oc1..aaaa").id,
            "vcpu": 2.0,
            "memory_gbs": 12.0,
            "vnic_id": "ocid1.vnic.oc1..aaaavnic",
            "public_ip": "129.1.1.1",
            "private_ip": "10.0.0.10",
        },
    )

    response = service.get_import_preview("ocid1.instance.oc1.sa-saopaulo-1.autoa1")

    assert response.already_registered is True
    assert response.name == "Instance A1"
    assert response.compartment_ocid == "ocid1.compartment.oc1..aaaa"
    assert response.compartment_name == "Compartment A"
    assert response.public_ip == "129.1.1.1"


def test_get_import_preview_returns_local_data_when_instance_exists_even_if_oci_fails(override_session):
    CompartmentService(override_session, fake_oci_service).list_and_update()
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="Instance A1",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
            description="existente",
            enabled=True,
        )
    )
    service.instances.apply_updates(
        created,
        {
            "compartment_id": service.compartments.get_by_ocid("ocid1.compartment.oc1..aaaa").id,
            "vcpu": 2.0,
            "memory_gbs": 12.0,
            "vnic_id": "ocid1.vnic.oc1..aaaavnic",
            "public_ip": "129.1.1.1",
            "private_ip": "10.0.0.10",
        },
    )
    original_lookup = fake_oci_service.get_instance_details
    fake_oci_service.get_instance_details = lambda _: (_ for _ in ()).throw(RuntimeError("oci_instance_not_found_or_forbidden"))

    try:
        response = service.get_import_preview("ocid1.instance.oc1.sa-saopaulo-1.autoa1")
    finally:
        fake_oci_service.get_instance_details = original_lookup

    assert response.already_registered is True
    assert response.ocid == "ocid1.instance.oc1.sa-saopaulo-1.autoa1"
    assert response.compartment_name == "Compartment A"


def test_import_instance_creates_local_record_with_oci_details(override_session):
    service = InstanceService(override_session, fake_oci_service)

    response = import_instance(
        InstanceImportCreate(
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
            description="instancia importada",
            enabled=False,
        ),
        CurrentUser(subject="local", email=None, groups=[]),
        service,
    )

    assert response.name == "Instance A1"
    assert response.ocid == "ocid1.instance.oc1.sa-saopaulo-1.autoa1"
    assert response.description == "instancia importada"
    assert response.enabled is False
    assert response.compartment_id is not None
    assert response.vcpu == 2.0
    assert response.memory_gbs == 12.0
    assert response.public_ip == "129.1.1.1"
    assert response.private_ip == "10.0.0.10"


def test_import_instance_rejects_duplicate_ocid(override_session):
    service = InstanceService(override_session, fake_oci_service)
    service.create_instance(
        InstanceCreate(
            name="Instance A1",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
            description=None,
            enabled=True,
        )
    )

    try:
        service.import_instance("ocid1.instance.oc1.sa-saopaulo-1.autoa1", "duplicada", True)
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Expected duplicate imported instance to raise HTTPException")


def test_import_instance_creates_missing_compartment_from_oci_lookup(override_session):
    service = InstanceService(override_session, fake_oci_service)

    created = service.import_instance("ocid1.instance.oc1.sa-saopaulo-1.autoa1", None, True)

    assert created.compartment_id is not None
    compartment = service.compartments.get_by_ocid("ocid1.compartment.oc1..aaaa")
    assert compartment is not None
    assert compartment.name == "Compartment A"
    assert compartment.active is True


def test_import_all_compartment_instances_creates_records_and_enriches_network_fields(override_session):
    CompartmentService(override_session, fake_oci_service).list_and_update()
    service = InstanceService(override_session, fake_oci_service)
    result = import_all_compartment_instances(CurrentUser(subject="local", email=None, groups=[]), service)

    assert result.total_compartments == 2
    assert result.total_instances == 2
    assert result.created == 2
    assert result.updated == 0
    assert result.unchanged == 0
    assert result.failed == 0

    instances = service.list_instances()
    by_ocid = {item.ocid: item for item in instances}
    first = by_ocid["ocid1.instance.oc1.sa-saopaulo-1.autoa1"]
    second = by_ocid["ocid1.instance.oc1.sa-saopaulo-1.autob1"]

    assert first.vcpu == 2.0
    assert first.memory_gbs == 12.0
    assert first.vnic_id == "ocid1.vnic.oc1..aaaavnic"
    assert first.public_ip == "129.1.1.1"
    assert first.private_ip == "10.0.0.10"
    assert first.oci_created_at is not None
    assert first.compartment_id is not None
    assert first.enabled is True
    assert first.description is None

    assert second.vnic_id == "ocid1.vnic.oc1..bbbbvnic"
    assert second.public_ip is None
    assert second.private_ip == "10.0.1.10"


def test_import_all_compartment_instances_updates_existing_ocid_and_preserves_local_fields(override_session):
    CompartmentService(override_session, fake_oci_service).list_and_update()
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="Nome Antigo",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
            description="manter",
            enabled=False,
        )
    )
    created.last_known_state = "STOPPED"
    override_session.add(created)
    override_session.commit()

    result = service.import_all_compartment_instances()
    updated = service.instances.get_by_ocid("ocid1.instance.oc1.sa-saopaulo-1.autoa1")

    assert result.created == 1
    assert result.updated == 1
    assert updated is not None
    assert updated.name == "Instance A1"
    assert updated.description == "manter"
    assert updated.enabled is False
    assert updated.last_known_state == "STOPPED"
    assert updated.compartment_id is not None
    assert updated.vcpu == 2.0
    assert updated.public_ip == "129.1.1.1"


def test_get_instance_vnic_route_returns_primary_vnic(override_session):
    service = InstanceService(override_session, fake_oci_service)

    response = get_instance_vnic(
        "ocid1.instance.oc1.sa-saopaulo-1.autoa1",
        CurrentUser(subject="local", email=None, groups=[]),
        service,
    )

    assert response.instance_ocid == "ocid1.instance.oc1.sa-saopaulo-1.autoa1"
    assert response.vnic_id == "ocid1.vnic.oc1..aaaavnic"


def test_get_vnic_details_route_returns_public_and_private_ip(override_session):
    service = InstanceService(override_session, fake_oci_service)

    response = get_vnic_details(
        "ocid1.vnic.oc1..aaaavnic",
        CurrentUser(subject="local", email=None, groups=[]),
        service,
    )

    assert response.vnic_id == "ocid1.vnic.oc1..aaaavnic"
    assert response.public_ip == "129.1.1.1"
    assert response.private_ip == "10.0.0.10"


def test_import_all_compartment_instances_handles_missing_vnic_without_failing(override_session):
    CompartmentService(override_session, fake_oci_service).list_and_update()
    fake_oci_service.vnic_ids["ocid1.instance.oc1.sa-saopaulo-1.autoa1"] = None
    service = InstanceService(override_session, fake_oci_service)

    result = service.import_all_compartment_instances()
    imported = service.instances.get_by_ocid("ocid1.instance.oc1.sa-saopaulo-1.autoa1")

    assert result.failed == 0
    assert imported is not None
    assert imported.vnic_id is None
    assert imported.public_ip is None
    assert imported.private_ip is None
