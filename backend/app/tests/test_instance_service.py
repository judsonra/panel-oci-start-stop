from fastapi import HTTPException

from app.api.routes import (
    create_instance,
    get_instance_import_preview,
    start_instance,
    get_instance_vnic,
    refresh_instance_statuses,
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
    created.last_known_state = "STOPPED"
    override_session.add(created)
    override_session.commit()
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
    created.last_known_state = "STOPPED"
    override_session.add(created)
    override_session.commit()
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


def test_start_instance_rejects_non_stopped_status(override_session):
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="VM Running",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.running",
            description="instancia ligada",
            enabled=True,
        )
    )
    created.last_known_state = "RUNNING"
    override_session.add(created)
    override_session.commit()

    called = False
    original_start_instance = fake_oci_service.start_instance

    def fail_if_called(_: str):
        nonlocal called
        called = True
        return original_start_instance(_)

    fake_oci_service.start_instance = fail_if_called
    try:
        try:
            service.start(created.id)
        except HTTPException as exc:
            assert exc.status_code == 400
            assert exc.detail == "Instance can only be started when enabled and with status STOPPED"
        else:
            raise AssertionError("Expected invalid state to raise HTTPException")
    finally:
        fake_oci_service.start_instance = original_start_instance

    assert called is False


def test_start_route_returns_instance_state(override_session):
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="VM Route Start",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.routestart",
            description="instancia rota",
            enabled=True,
        )
    )
    created.last_known_state = "STOPPED"
    override_session.add(created)
    override_session.commit()

    response = start_instance(created.id, CurrentUser(subject="local", email=None, groups=[]), service)

    assert response.instance_id == created.id
    assert response.instance_state == "RUNNING"
    assert response.status == ExecutionStatus.success


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


def test_import_instance_upsert_returns_preview_when_ocid_is_not_registered(override_session):
    service = InstanceService(override_session, fake_oci_service)

    result = service.import_instance_upsert("ocid1.instance.oc1.sa-saopaulo-1.autoa1")

    assert result.mode == "not_registered"
    assert result.instance is None
    assert result.preview is not None
    assert result.preview.ocid == "ocid1.instance.oc1.sa-saopaulo-1.autoa1"
    assert result.preview.compartment_name == "Compartment A"


def test_import_instance_upsert_updates_existing_and_preserves_manual_fields(override_session):
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="Nome Local",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
            description="manter",
            enabled=False,
            app_url="manual.docnix.com.br",
        )
    )
    updated_name = "OCIXDOC-HMG-Cliente Novo"
    fake_oci_service.instance_details["ocid1.instance.oc1.sa-saopaulo-1.autoa1"] = fake_oci_service.instance_details[
        "ocid1.instance.oc1.sa-saopaulo-1.autoa1"
    ].__class__(
        name=updated_name,
        ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
        compartment_ocid="ocid1.compartment.oc1..aaaa",
        vcpu=6.0,
        memory_gbs=32.0,
        oci_created_at=fake_oci_service.instance_details["ocid1.instance.oc1.sa-saopaulo-1.autoa1"].oci_created_at,
    )

    result = service.import_instance_upsert("ocid1.instance.oc1.sa-saopaulo-1.autoa1")

    assert result.mode == "updated"
    assert result.preview is None
    assert result.instance is not None
    assert result.instance.name == updated_name
    assert result.instance.description == "manter"
    assert result.instance.enabled is False
    assert result.instance.vcpu == 6.0
    assert result.instance.memory_gbs == 32.0
    assert result.instance.app_url == "cliente-novohmg.docnix.com.br"
    assert result.instance.environment == "HMG"
    assert result.instance.customer_name == "cliente-novo"
    assert result.instance.domain == "docnix.com.br"
    assert result.instance.name_prefix == "OCIXDOC"
    assert result.instance.id == created.id


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
    fake_oci_service.instances_by_compartment["ocid1.compartment.oc1..aaaa"][0] = fake_oci_service.instances_by_compartment[
        "ocid1.compartment.oc1..aaaa"
    ][0].__class__(
        name="OCIXDOC-HMG-Cliente Sync",
        ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
        lifecycle_state="RUNNING",
        vcpu=2.0,
        memory_gbs=12.0,
        oci_created_at=fake_oci_service.instances_by_compartment["ocid1.compartment.oc1..aaaa"][0].oci_created_at,
    )
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="Nome Antigo",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
            description="manter",
            enabled=False,
            app_url="manual-lock.docnix.com.br",
            environment="PRD",
            customer_name="manual",
            domain="pmrun.com.br",
            name_prefix="OCIARQ",
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
    assert updated.app_url == "cliente-synchmg.docnix.com.br"
    assert updated.environment == "HMG"
    assert updated.customer_name == "cliente-sync"
    assert updated.domain == "docnix.com.br"
    assert updated.name_prefix == "OCIXDOC"


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


def test_refresh_statuses_by_compartment_updates_only_registered_instances(override_session):
    CompartmentService(override_session, fake_oci_service).list_and_update()
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="Instance A1",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
            description="local",
            enabled=False,
        )
    )
    created.compartment_id = service.compartments.get_by_ocid("ocid1.compartment.oc1..aaaa").id
    created.last_known_state = "STOPPED"
    override_session.add(created)
    override_session.commit()

    result = service.refresh_statuses_by_compartment()
    updated = service.instances.get_by_ocid("ocid1.instance.oc1.sa-saopaulo-1.autoa1")
    missing = service.instances.get_by_ocid("ocid1.instance.oc1.sa-saopaulo-1.autob1")

    assert result.total_compartments == 2
    assert result.processed_compartments == 2
    assert result.matched_instances == 1
    assert result.updated == 1
    assert result.unchanged == 0
    assert result.failed == 0
    assert updated is not None
    assert updated.last_known_state == "RUNNING"
    assert updated.description == "local"
    assert updated.enabled is False
    assert missing is None


def test_refresh_statuses_by_compartment_ignores_unchanged_states(override_session):
    CompartmentService(override_session, fake_oci_service).list_and_update()
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="Instance A1",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
            description=None,
            enabled=True,
        )
    )
    created.compartment_id = service.compartments.get_by_ocid("ocid1.compartment.oc1..aaaa").id
    created.last_known_state = "RUNNING"
    override_session.add(created)
    override_session.commit()

    result = service.refresh_statuses_by_compartment()

    assert result.matched_instances == 1
    assert result.updated == 0
    assert result.unchanged == 1


def test_refresh_statuses_by_compartment_continues_after_compartment_failure(override_session):
    CompartmentService(override_session, fake_oci_service).list_and_update()
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="Instance A1",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
            description=None,
            enabled=True,
        )
    )
    created.compartment_id = service.compartments.get_by_ocid("ocid1.compartment.oc1..aaaa").id
    override_session.add(created)
    override_session.commit()
    original_list = fake_oci_service.list_instances_by_compartment

    def failing_list(compartment_ocid: str):
        if compartment_ocid == "ocid1.compartment.oc1..bbbb":
            raise RuntimeError("oci_compartment_failed")
        return original_list(compartment_ocid)

    fake_oci_service.list_instances_by_compartment = failing_list
    try:
        result = service.refresh_statuses_by_compartment()
    finally:
        fake_oci_service.list_instances_by_compartment = original_list

    assert result.processed_compartments == 2
    assert result.updated == 1
    assert result.failed == 1
    assert any(item.compartment_ocid == "ocid1.compartment.oc1..bbbb" and item.failed == 1 for item in result.compartments)


def test_refresh_statuses_route_returns_summary(override_session):
    CompartmentService(override_session, fake_oci_service).list_and_update()
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="Instance A1",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
            description=None,
            enabled=True,
        )
    )
    created.compartment_id = service.compartments.get_by_ocid("ocid1.compartment.oc1..aaaa").id
    override_session.add(created)
    override_session.commit()

    response = refresh_instance_statuses(CurrentUser(subject="local", email=None, groups=[]), service)

    assert response.total_compartments == 2
    assert response.updated == 1
    assert response.compartments[0].compartment_ocid.startswith("ocid1.compartment.")


def test_create_instance_derives_routing_fields_from_name(override_session):
    service = InstanceService(override_session, fake_oci_service)

    created = service.create_instance(
        InstanceCreate(
            name="OCIXDOC-HMG-CLIENTE-ALPHA",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.routing1",
            description=None,
            enabled=True,
        )
    )

    assert created.environment == "HMG"
    assert created.customer_name == "cliente-alpha"
    assert created.domain == "docnix.com.br"
    assert created.name_prefix == "OCIXDOC"
    assert created.app_url == "cliente-alphahmg.docnix.com.br"


def test_create_instance_rejects_duplicate_app_url(override_session):
    service = InstanceService(override_session, fake_oci_service)
    service.create_instance(
        InstanceCreate(
            name="OCIXDOC-PRD-CLIENTE-A",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.dupappa",
            app_url="clientea.docnix.com.br",
            description=None,
            enabled=True,
        )
    )

    try:
        service.create_instance(
            InstanceCreate(
                name="OCIXPM-PRD-CLIENTE-A",
                ocid="ocid1.instance.oc1.sa-saopaulo-1.dupappb",
                app_url="clientea.docnix.com.br",
                description=None,
                enabled=True,
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Expected duplicate app_url to raise HTTPException")


def test_get_import_preview_returns_derived_url_fields(override_session):
    service = InstanceService(override_session, fake_oci_service)
    fake_oci_service.instance_details["ocid1.instance.oc1.sa-saopaulo-1.autoa1"] = fake_oci_service.instance_details[
        "ocid1.instance.oc1.sa-saopaulo-1.autoa1"
    ].__class__(
        name="OCIXPM-PRD-CLIENTE-BETA",
        ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
        compartment_ocid="ocid1.compartment.oc1..aaaa",
        vcpu=2.0,
        memory_gbs=12.0,
        oci_created_at=fake_oci_service.instance_details["ocid1.instance.oc1.sa-saopaulo-1.autoa1"].oci_created_at,
    )

    preview = service.get_import_preview("ocid1.instance.oc1.sa-saopaulo-1.autoa1")

    assert preview.environment == "PRD"
    assert preview.domain == "pmrun.com.br"
    assert preview.app_url == "cliente-beta.pmrun.com.br"


def test_proxy_resolve_returns_pass_when_running(override_session):
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="OCIXDOC-PRD-CLIENTE-RUN",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.proxyrun",
            app_url="clienterun.docnix.com.br",
            description=None,
            enabled=True,
        )
    )

    original_status = fake_oci_service.get_status
    fake_oci_service.get_status = lambda _: original_status(created.ocid)
    try:
        result = service.resolve_for_proxy("clienterun.docnix.com.br", cooldown_seconds=60)
    finally:
        fake_oci_service.get_status = original_status

    assert result.decision == "pass"
    assert result.instance_id == created.id
    assert result.ocid == created.ocid


def test_proxy_resolve_starts_when_stopped_and_waits(override_session):
    service = InstanceService(override_session, fake_oci_service)
    created = service.create_instance(
        InstanceCreate(
            name="OCIXDOC-PRD-CLIENTE-STOP",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.proxystop",
            app_url="clientestop.docnix.com.br",
            description=None,
            enabled=True,
        )
    )

    original_status = fake_oci_service.get_status
    original_start = fake_oci_service.start_instance

    def stopped_status(_: str):
        result = original_status(created.ocid)
        result.state = "STOPPED"
        return result

    fake_oci_service.get_status = stopped_status
    fake_oci_service.start_instance = original_start
    try:
        result = service.resolve_for_proxy("clientestop.docnix.com.br", cooldown_seconds=60)
    finally:
        fake_oci_service.get_status = original_status
        fake_oci_service.start_instance = original_start

    assert result.decision == "wait"
    assert result.state in {"RUNNING", "STARTING"}
    assert result.message is not None


def test_proxy_resolve_returns_not_found_when_host_is_unknown(override_session):
    service = InstanceService(override_session, fake_oci_service)

    result = service.resolve_for_proxy("inexistente.docnix.com.br", cooldown_seconds=60)

    assert result.decision == "not_found"


def test_backfill_missing_app_urls_updates_only_missing_values(override_session):
    service = InstanceService(override_session, fake_oci_service)
    missing = service.create_instance(
        InstanceCreate(
            name="OCIXDOC-HMG-CLIENTE-NEW",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.backfilla",
            app_url=None,
            description=None,
            enabled=True,
        )
    )
    existing = service.create_instance(
        InstanceCreate(
            name="OCIXDOC-PRD-CLIENTE-LOCKED",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.backfillb",
            app_url="manual-lock.docnix.com.br",
            description=None,
            enabled=True,
        )
    )

    result = service.backfill_missing_app_urls()
    updated_missing = service.get_instance(missing.id)
    same_existing = service.get_instance(existing.id)

    assert result.total == 1
    assert result.updated == 1
    assert result.unresolved == 0
    assert updated_missing.app_url == "cliente-newhmg.docnix.com.br"
    assert same_existing.app_url == "manual-lock.docnix.com.br"


def test_backfill_missing_app_urls_marks_unresolved_when_name_cannot_be_derived(override_session):
    service = InstanceService(override_session, fake_oci_service)
    service.create_instance(
        InstanceCreate(
            name="INSTANCIA-SEM-PADRAO",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.backfillc",
            app_url=None,
            description=None,
            enabled=True,
        )
    )

    result = service.backfill_missing_app_urls()

    assert result.total == 1
    assert result.updated == 0
    assert result.unresolved == 1
    assert result.items[0].outcome == "unresolved"


def test_backfill_missing_app_urls_continues_when_one_item_fails(override_session):
    service = InstanceService(override_session, fake_oci_service)
    failing = service.create_instance(
        InstanceCreate(
            name="OCIXDOC-HMG-CLIENTE-FAIL",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.backfilld",
            app_url=None,
            description=None,
            enabled=True,
        )
    )
    service.create_instance(
        InstanceCreate(
            name="OCIXDOC-HMG-CLIENTE-OK",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.backfille",
            app_url=None,
            description=None,
            enabled=True,
        )
    )

    original_apply_updates = service.instances.apply_updates

    def fail_once(instance, updates):
        if instance.id == failing.id:
            raise RuntimeError("forced_backfill_failure")
        return original_apply_updates(instance, updates)

    service.instances.apply_updates = fail_once
    try:
        result = service.backfill_missing_app_urls()
    finally:
        service.instances.apply_updates = original_apply_updates

    assert result.total == 2
    assert result.failed == 1
    assert result.updated == 1
