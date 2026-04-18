from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import Settings
from app.services.oci_cli import OCIService


def make_settings() -> Settings:
    return Settings(
        database_url="sqlite:///./test.db",
        auth_enabled=False,
        scheduler_enabled=False,
        oci_cli_path="oci",
        oci_cli_profile="DEFAULT",
        oci_config_dir="/tmp/mock-oci",
    )


def mock_parser_with_key_file(relative_key_file: str = "api.pem"):
    return {"DEFAULT": {"key_file": relative_key_file}}


def test_start_command_generation():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=True):
            with patch("app.services.oci_cli.configparser.ConfigParser.read"):
                with patch("app.services.oci_cli.configparser.ConfigParser.__contains__", return_value=True):
                    with patch("app.services.oci_cli.configparser.ConfigParser.__getitem__", return_value={"key_file": "api.pem"}):
                        with patch("app.services.oci_cli.subprocess.run") as run_mock:
                            run_mock.return_value = SimpleNamespace(returncode=0, stdout='{"data":{"lifecycle-state":"RUNNING"}}', stderr="")
                            result = service.start_instance("ocid1.instance.oc1.sa-saopaulo-1.start")
    assert result.success is True
    assert result.command[:5] == ["oci", "compute", "instance", "action", "--action"]
    assert result.command[5] == "START"


def test_stop_command_generation():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=True):
            with patch("app.services.oci_cli.configparser.ConfigParser.read"):
                with patch("app.services.oci_cli.configparser.ConfigParser.__contains__", return_value=True):
                    with patch("app.services.oci_cli.configparser.ConfigParser.__getitem__", return_value={"key_file": "api.pem"}):
                        with patch("app.services.oci_cli.subprocess.run") as run_mock:
                            run_mock.return_value = SimpleNamespace(returncode=0, stdout='{"data":{"lifecycle-state":"STOPPED"}}', stderr="")
                            result = service.stop_instance("ocid1.instance.oc1.sa-saopaulo-1.stop")
    assert result.success is True
    assert "STOP" in result.command


def test_get_command_generation():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=True):
            with patch("app.services.oci_cli.configparser.ConfigParser.read"):
                with patch("app.services.oci_cli.configparser.ConfigParser.__contains__", return_value=True):
                    with patch("app.services.oci_cli.configparser.ConfigParser.__getitem__", return_value={"key_file": "api.pem"}):
                        with patch("app.services.oci_cli.subprocess.run") as run_mock:
                            run_mock.return_value = SimpleNamespace(returncode=0, stdout='{"data":{"lifecycle-state":"RUNNING"}}', stderr="")
                            result = service.get_status("ocid1.instance.oc1.sa-saopaulo-1.status")
    assert result.success is True
    assert result.command[:4] == ["oci", "compute", "instance", "get"]


def test_restart_command_generation():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=True):
            with patch("app.services.oci_cli.configparser.ConfigParser.read"):
                with patch("app.services.oci_cli.configparser.ConfigParser.__contains__", return_value=True):
                    with patch("app.services.oci_cli.configparser.ConfigParser.__getitem__", return_value={"key_file": "api.pem"}):
                        with patch("app.services.oci_cli.subprocess.run") as run_mock:
                            run_mock.return_value = SimpleNamespace(returncode=0, stdout='{"data":{"lifecycle-state":"RUNNING"}}', stderr="")
                            result = service.restart_instance("ocid1.instance.oc1.sa-saopaulo-1.restart")
    assert result.success is True
    assert "SOFTRESET" in result.command


def test_missing_cli_is_reported():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value=None):
        result = service.start_instance("ocid1.instance.oc1.sa-saopaulo-1.missingcli")
    assert result.success is False
    assert result.return_code == 127
    assert result.parsed_error == "OCI CLI not found in PATH for 'oci'"


def test_missing_config_is_reported():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=False):
            result = service.start_instance("ocid1.instance.oc1.sa-saopaulo-1.missingconfig")
    assert result.success is False
    assert result.return_code == 2
    assert result.parsed_error == "OCI config file not found at '/tmp/mock-oci/config'"


def test_permission_denied_is_parsed():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=True):
            with patch("app.services.oci_cli.configparser.ConfigParser.read"):
                with patch("app.services.oci_cli.configparser.ConfigParser.__contains__", return_value=True):
                    with patch("app.services.oci_cli.configparser.ConfigParser.__getitem__", return_value={"key_file": "api.pem"}):
                        with patch("app.services.oci_cli.subprocess.run") as run_mock:
                            run_mock.return_value = SimpleNamespace(returncode=1, stdout="", stderr="NotAuthorized")
                            result = service.start_instance("ocid1.instance.oc1.sa-saopaulo-1.denied")
    assert result.success is False
    assert result.parsed_error == "oci_permission_denied"


def test_missing_relative_key_file_is_reported():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch.object(OCIService, "resolved_key_file", return_value="/tmp/mock-oci/api.pem"):
            with patch("app.services.oci_cli.Path.is_file", side_effect=[True, False]):
                result = service.start_instance("ocid1.instance.oc1.sa-saopaulo-1.keymissing")
    assert result.success is False
    assert result.return_code == 3
    assert result.parsed_error == "OCI key file not found at '/tmp/mock-oci/api.pem'"


def test_run_uses_oci_config_dir_as_cwd():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=True):
            with patch("app.services.oci_cli.configparser.ConfigParser.read"):
                with patch("app.services.oci_cli.configparser.ConfigParser.__contains__", return_value=True):
                    with patch("app.services.oci_cli.configparser.ConfigParser.__getitem__", return_value={"key_file": "api.pem"}):
                        with patch("app.services.oci_cli.subprocess.run") as run_mock:
                            run_mock.return_value = SimpleNamespace(returncode=0, stdout='{"data":{"lifecycle-state":"RUNNING"}}', stderr="")
                            service.start_instance("ocid1.instance.oc1.sa-saopaulo-1.cwd")
    assert run_mock.call_args.kwargs["cwd"] == "/tmp/mock-oci"


def test_resolve_tenant_id_uses_setting_when_available():
    settings = make_settings().model_copy(update={"oci_tenant_id": "ocid1.tenancy.oc1..tenant"})
    service = OCIService(settings)

    assert service.resolve_tenant_id() == "ocid1.tenancy.oc1..tenant"


def test_resolve_tenant_id_uses_config_tenancy_when_setting_is_empty():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.Path.is_file", return_value=True):
        with patch("app.services.oci_cli.configparser.ConfigParser.read"):
            with patch("app.services.oci_cli.configparser.ConfigParser.__contains__", return_value=True):
                with patch("app.services.oci_cli.configparser.ConfigParser.__getitem__", return_value={"tenancy": "ocid1.tenancy.oc1..configtenant"}):
                    assert service.resolve_tenant_id() == "ocid1.tenancy.oc1..configtenant"


def test_resolve_tenant_id_raises_when_not_configured():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.Path.is_file", return_value=True):
        with patch("app.services.oci_cli.configparser.ConfigParser.read"):
            with patch("app.services.oci_cli.configparser.ConfigParser.__contains__", return_value=True):
                with patch("app.services.oci_cli.configparser.ConfigParser.__getitem__", return_value={}):
                    try:
                        service.resolve_tenant_id()
                    except RuntimeError as exc:
                        assert "OCI tenancy not configured" in str(exc)
                    else:
                        raise AssertionError("Expected missing tenancy to raise RuntimeError")


def test_list_compartments_command_generation_and_parsing():
    settings = make_settings().model_copy(update={"oci_tenant_id": "ocid1.tenancy.oc1..tenant"})
    service = OCIService(settings)
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=True):
            with patch.object(OCIService, "resolved_key_file", return_value="/tmp/mock-oci/api.pem"):
                with patch("app.services.oci_cli.subprocess.run") as run_mock:
                    run_mock.return_value = SimpleNamespace(
                        returncode=0,
                        stdout='{"data":[{"name":"Root","id":"ocid1.compartment.oc1..root"},{"name":"Apps","id":"ocid1.compartment.oc1..apps"}]}',
                        stderr="",
                    )
                    result = service.list_compartments()
    assert [item.name for item in result] == ["Root", "Apps"]
    assert run_mock.call_args.args[0][:4] == ["oci", "iam", "compartment", "list"]


def test_list_instances_by_compartment_command_generation_and_parsing():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=True):
            with patch.object(OCIService, "resolved_key_file", return_value="/tmp/mock-oci/api.pem"):
                with patch("app.services.oci_cli.subprocess.run") as run_mock:
                    run_mock.return_value = SimpleNamespace(
                        returncode=0,
                        stdout='{"data":[{"nome":"VM A","id":"ocid1.instance.oc1..a","lifecycleState":"RUNNING","vcpus":2,"memoria":12,"criadoEm":"2026-03-20T10:00:00+00:00"}]}',
                        stderr="",
                    )
                    result = service.list_instances_by_compartment("ocid1.compartment.oc1..aaaa")
    assert len(result) == 1
    assert result[0].name == "VM A"
    assert result[0].ocid == "ocid1.instance.oc1..a"
    assert result[0].lifecycle_state == "RUNNING"
    assert run_mock.call_args.args[0][:4] == ["oci", "compute", "instance", "list"]


def test_get_instance_details_parses_payload_with_nested_data():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=True):
            with patch.object(OCIService, "resolved_key_file", return_value="/tmp/mock-oci/api.pem"):
                with patch("app.services.oci_cli.subprocess.run") as run_mock:
                    run_mock.return_value = SimpleNamespace(
                        returncode=0,
                        stdout='{"data":{"name":"VM A","id":"ocid1.instance.oc1..a","compartmentId":"ocid1.compartment.oc1..aaaa","vcpus":2,"memory":12,"created":"2026-03-20T10:00:00+00:00"}}',
                        stderr="",
                    )
                    result = service.get_instance_details("ocid1.instance.oc1..a")
    assert result.name == "VM A"
    assert result.ocid == "ocid1.instance.oc1..a"
    assert result.compartment_ocid == "ocid1.compartment.oc1..aaaa"
    assert result.vcpu == 2.0
    assert result.memory_gbs == 12.0
    assert result.oci_created_at is not None
    assert run_mock.call_args.args[0][:4] == ["oci", "compute", "instance", "get"]


def test_get_instance_details_parses_payload_without_nested_data():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=True):
            with patch.object(OCIService, "resolved_key_file", return_value="/tmp/mock-oci/api.pem"):
                with patch("app.services.oci_cli.subprocess.run") as run_mock:
                    run_mock.return_value = SimpleNamespace(
                        returncode=0,
                        stdout='{"name":"VM B","id":"ocid1.instance.oc1..b","compartmentId":"ocid1.compartment.oc1..bbbb","vcpus":4,"memory":24,"created":"2026-03-21T10:00:00+00:00"}',
                        stderr="",
                    )
                    result = service.get_instance_details("ocid1.instance.oc1..b")
    assert result.name == "VM B"
    assert result.ocid == "ocid1.instance.oc1..b"
    assert result.compartment_ocid == "ocid1.compartment.oc1..bbbb"
    assert result.vcpu == 4.0
    assert result.memory_gbs == 24.0
    assert result.oci_created_at is not None


def test_get_instance_details_raises_when_payload_has_no_object_data():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=True):
            with patch.object(OCIService, "resolved_key_file", return_value="/tmp/mock-oci/api.pem"):
                with patch("app.services.oci_cli.subprocess.run") as run_mock:
                    run_mock.return_value = SimpleNamespace(
                        returncode=0,
                        stdout='{"data":[]}',
                        stderr="",
                    )
                    try:
                        service.get_instance_details("ocid1.instance.oc1..x")
                    except RuntimeError as exc:
                        assert str(exc) == "OCI instance lookup did not return instance data"
                    else:
                        raise AssertionError("Expected invalid payload to raise RuntimeError")


def test_get_instance_details_raises_when_required_fields_are_missing():
    service = OCIService(make_settings())
    with patch("app.services.oci_cli.shutil.which", return_value="/usr/bin/oci"):
        with patch("app.services.oci_cli.Path.is_file", return_value=True):
            with patch.object(OCIService, "resolved_key_file", return_value="/tmp/mock-oci/api.pem"):
                with patch("app.services.oci_cli.subprocess.run") as run_mock:
                    run_mock.return_value = SimpleNamespace(
                        returncode=0,
                        stdout='{"name":"VM C","id":"ocid1.instance.oc1..c"}',
                        stderr="",
                    )
                    try:
                        service.get_instance_details("ocid1.instance.oc1..c")
                    except RuntimeError as exc:
                        assert str(exc) == "OCI instance lookup returned incomplete instance data"
                    else:
                        raise AssertionError("Expected incomplete payload to raise RuntimeError")
