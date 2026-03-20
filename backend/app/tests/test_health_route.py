from app.api.routes import health
from app.schemas.common import HealthResponse


class HealthyOCIService:
    def health_status(self):
        return type(
            "OCIHealth",
            (),
            {
                "cli_available": True,
                "config_available": True,
                "cli_version": "3.0.0",
                "cli_path": "/usr/bin/oci",
                "config_file": "/home/appuser/.oci/config",
                "key_file": "/home/appuser/.oci/api.pem",
                "key_file_exists": True,
                "error": None,
            },
        )()


class FailingSession:
    def execute(self, *_args, **_kwargs):
        raise RuntimeError("db down")


class WorkingSession:
    def execute(self, *_args, **_kwargs):
        return 1


def test_health_reports_ok_when_dependencies_are_available():
    response = health(WorkingSession(), HealthyOCIService())
    assert isinstance(response, HealthResponse)
    assert response.status == "ok"
    assert response.database == "ok"
    assert response.oci_cli == "ok"
    assert response.oci_config == "ok"
    assert response.details["oci_key_file"] == "/home/appuser/.oci/api.pem"
    assert response.details["oci_key_file_exists"] == "True"


def test_health_reports_degraded_when_database_fails():
    response = health(FailingSession(), HealthyOCIService())
    assert response.status == "degraded"
    assert response.database == "error"
