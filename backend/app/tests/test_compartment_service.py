from app.api.routes import list_and_update_compartments, list_compartments
from app.core.security import CurrentUser
from app.models.compartment import Compartment
from app.services.compartment_service import CompartmentService
from app.services.oci_cli import OCICompartmentSummary
from app.tests.conftest import fake_oci_service


def test_list_compartments_returns_persisted_records_without_sync(override_session):
    service = CompartmentService(override_session, fake_oci_service)
    service.list_and_update()
    fake_oci_service.compartments = []

    compartments = service.list_compartments()

    assert len(compartments) == 2
    assert all(item.ocid.startswith("ocid1.compartment.") for item in compartments)


def test_list_and_update_compartments_creates_records(override_session):
    service = CompartmentService(override_session, fake_oci_service)

    compartments = service.list_and_update()

    assert len(compartments) == 2
    assert compartments[0].active is True
    assert override_session.query(Compartment).count() == 2


def test_list_and_update_compartments_updates_name_and_deactivates_missing(override_session):
    service = CompartmentService(override_session, fake_oci_service)
    service.list_and_update()

    fake_oci_service.compartments = [
        OCICompartmentSummary(name="Compartment A Renamed", ocid="ocid1.compartment.oc1..aaaa"),
    ]

    compartments = service.list_and_update()
    by_ocid = {item.ocid: item for item in compartments}

    assert by_ocid["ocid1.compartment.oc1..aaaa"].name == "Compartment A Renamed"
    assert by_ocid["ocid1.compartment.oc1..aaaa"].active is True
    assert by_ocid["ocid1.compartment.oc1..bbbb"].active is False


def test_list_and_update_compartments_route_returns_serialized_response(override_session):
    service = CompartmentService(override_session, fake_oci_service)

    response = list_and_update_compartments(CurrentUser(subject="local", email=None, groups=[]), service)

    assert len(response) == 2
    assert response[0].ocid.startswith("ocid1.compartment.")
    assert response[0].active is True


def test_list_compartments_route_returns_database_records(override_session):
    service = CompartmentService(override_session, fake_oci_service)
    service.list_and_update()
    fake_oci_service.compartments = []

    response = list_compartments(CurrentUser(subject="local", email=None, groups=[]), service)

    assert len(response) == 2
    assert response[0].ocid.startswith("ocid1.compartment.")
