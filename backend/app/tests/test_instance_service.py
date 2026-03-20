from fastapi import HTTPException

from app.api.routes import create_instance, get_status
from app.core.security import CurrentUser
from app.models.execution_log import ExecutionStatus
from app.schemas.instance import InstanceCreate
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
