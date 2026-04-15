from app.api.routes import resolve_proxy_host
from app.core.config import Settings
from app.schemas.instance import ProxyResolveRead
from app.schemas.instance import InstanceCreate
from app.services.instance_service import InstanceService
from app.tests.conftest import fake_oci_service


def test_resolve_proxy_host_returns_wait_when_instance_is_stopped(override_session):
    service = InstanceService(override_session, fake_oci_service)
    service.create_instance(
        InstanceCreate(
            name="OCIXDOC-PRD-CLIENTE-ROUTE",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.proxyroute",
            app_url="cliente-route.docnix.com.br",
            enabled=True,
        )
    )

    original_status = fake_oci_service.get_status

    def stopped_status(ocid: str):
        result = original_status(ocid)
        result.state = "STOPPED"
        return result

    fake_oci_service.get_status = stopped_status
    try:
        response = resolve_proxy_host(
            host="cliente-route.docnix.com.br",
            _=None,
            settings=Settings(proxy_start_cooldown_seconds=60),
            service=service,
        )
    finally:
        fake_oci_service.get_status = original_status

    assert isinstance(response, ProxyResolveRead)
    assert response.decision == "wait"
    assert response.ocid == "ocid1.instance.oc1.sa-saopaulo-1.proxyroute"
