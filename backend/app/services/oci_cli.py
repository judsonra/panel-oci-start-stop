import json
import configparser
import os
import shutil
import subprocess
import time
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings, get_settings


@dataclass
class OCICommandResult:
    state: str | None
    stdout: str | None
    stderr: str | None
    return_code: int
    command: list[str]
    duration_ms: int
    parsed_error: str | None = None

    @property
    def success(self) -> bool:
        return self.return_code == 0


@dataclass
class OCIHealthStatus:
    cli_available: bool
    config_available: bool
    cli_version: str | None
    cli_path: str | None
    config_file: str
    key_file: str | None
    key_file_exists: bool
    error: str | None = None


@dataclass
class OCICompartmentSummary:
    name: str
    ocid: str


@dataclass
class OCIInstanceSummary:
    name: str
    ocid: str
    vcpu: float | None
    memory_gbs: float | None
    oci_created_at: datetime | None


@dataclass
class OCIInstanceDetails:
    name: str
    ocid: str
    compartment_ocid: str
    vcpu: float | None
    memory_gbs: float | None
    oci_created_at: datetime | None


@dataclass
class OCIVnicDetails:
    vnic_id: str
    public_ip: str | None
    private_ip: str | None


class OCIService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def config_file(self) -> str:
        return f"{self.settings.oci_config_dir}/config"

    def resolved_key_file(self) -> str | None:
        config_path = Path(self.config_file)
        if not config_path.is_file():
            return None
        parser = configparser.ConfigParser()
        parser.read(config_path)
        if self.settings.oci_cli_profile not in parser:
            return None
        key_file = parser[self.settings.oci_cli_profile].get("key_file")
        if not key_file:
            return None
        key_path = Path(key_file)
        if key_path.is_absolute():
            return str(key_path)
        return str((Path(self.settings.oci_config_dir) / key_path).resolve())

    def resolve_tenant_id(self) -> str:
        if self.settings.oci_tenant_id:
            return self.settings.oci_tenant_id
        config_path = Path(self.config_file)
        if not config_path.is_file():
            raise RuntimeError(f"OCI config file not found at '{self.config_file}'")
        parser = configparser.ConfigParser()
        parser.read(config_path)
        if self.settings.oci_cli_profile not in parser:
            raise RuntimeError(f"OCI profile '{self.settings.oci_cli_profile}' not found in '{self.config_file}'")
        tenant_id = parser[self.settings.oci_cli_profile].get("tenancy")
        if not tenant_id:
            raise RuntimeError("OCI tenancy not configured. Set OCI_TENANT_ID or configure tenancy in OCI config.")
        return tenant_id

    def health_status(self) -> OCIHealthStatus:
        config_path = Path(self.config_file)
        key_file = self.resolved_key_file()
        resolved_cli = shutil.which(self.settings.oci_cli_path)
        cli_version = None
        error = None
        if resolved_cli:
            try:
                completed = subprocess.run(
                    [self.settings.oci_cli_path, "--version"],
                    capture_output=True,
                    text=True,
                    env={**os.environ, "OCI_CLI_CONFIG_FILE": self.config_file},
                    check=False,
                )
                if completed.returncode == 0:
                    cli_version = (completed.stdout or completed.stderr).strip() or None
                else:
                    error = completed.stderr.strip() or "oci version command failed"
            except OSError as exc:
                error = str(exc)
        else:
            error = f"OCI CLI not found in PATH for '{self.settings.oci_cli_path}'"
        return OCIHealthStatus(
            cli_available=resolved_cli is not None,
            config_available=config_path.is_file(),
            cli_version=cli_version,
            cli_path=resolved_cli,
            config_file=str(config_path),
            key_file=key_file,
            key_file_exists=Path(key_file).is_file() if key_file else False,
            error=error,
        )

    def _run(self, args: list[str]) -> OCICommandResult:
        started = time.perf_counter()
        command = [self.settings.oci_cli_path, *args]
        if shutil.which(self.settings.oci_cli_path) is None:
            return OCICommandResult(
                state=None,
                stdout=None,
                stderr=None,
                return_code=127,
                command=command,
                duration_ms=0,
                parsed_error=f"OCI CLI not found in PATH for '{self.settings.oci_cli_path}'",
            )
        if not Path(self.config_file).is_file():
            return OCICommandResult(
                state=None,
                stdout=None,
                stderr=None,
                return_code=2,
                command=command,
                duration_ms=0,
                parsed_error=f"OCI config file not found at '{self.config_file}'",
            )
        resolved_key_file = self.resolved_key_file()
        if resolved_key_file is not None and not Path(resolved_key_file).is_file():
            return OCICommandResult(
                state=None,
                stdout=None,
                stderr=None,
                return_code=3,
                command=command,
                duration_ms=0,
                parsed_error=f"OCI key file not found at '{resolved_key_file}'",
            )
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                env={**os.environ, "OCI_CLI_CONFIG_FILE": self.config_file},
                check=False,
                cwd=self.settings.oci_config_dir,
            )
        except OSError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return OCICommandResult(
                state=None,
                stdout=None,
                stderr=None,
                return_code=126,
                command=command,
                duration_ms=duration_ms,
                parsed_error=str(exc),
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        state = None
        if completed.stdout:
            try:
                payload = json.loads(completed.stdout)
                if isinstance(payload, dict):
                    data = payload.get("data")
                    if isinstance(data, dict):
                        state = data.get("lifecycle-state")
            except json.JSONDecodeError:
                state = None
        stderr = completed.stderr.strip() or None
        return OCICommandResult(
            state=state,
            stdout=completed.stdout.strip() or None,
            stderr=stderr,
            return_code=completed.returncode,
            command=command,
            duration_ms=duration_ms,
            parsed_error=self._parse_error(stderr) if completed.returncode != 0 else None,
        )

    def start_instance(self, ocid: str) -> OCICommandResult:
        return self._run(
            [
                "compute",
                "instance",
                "action",
                "--action",
                "START",
                "--instance-id",
                ocid,
                "--profile",
                self.settings.oci_cli_profile,
                "--output",
                "json",
            ]
        )

    def stop_instance(self, ocid: str) -> OCICommandResult:
        return self._run(
            [
                "compute",
                "instance",
                "action",
                "--action",
                "STOP",
                "--instance-id",
                ocid,
                "--profile",
                self.settings.oci_cli_profile,
                "--output",
                "json",
            ]
        )

    def restart_instance(self, ocid: str) -> OCICommandResult:
        return self._run(
            [
                "compute",
                "instance",
                "action",
                "--action",
                "SOFTRESET",
                "--instance-id",
                ocid,
                "--profile",
                self.settings.oci_cli_profile,
                "--output",
                "json",
            ]
        )

    def get_status(self, ocid: str) -> OCICommandResult:
        return self._run(
            [
                "compute",
                "instance",
                "get",
                "--instance-id",
                ocid,
                "--profile",
                self.settings.oci_cli_profile,
                "--output",
                "json",
            ]
        )

    def list_compartments(self) -> list[OCICompartmentSummary]:
        result = self._run(
            [
                "iam",
                "compartment",
                "list",
                "--compartment-id",
                self.resolve_tenant_id(),
                "--compartment-id-in-subtree",
                "true",
                "--access-level",
                "ACCESSIBLE",
                "--profile",
                self.settings.oci_cli_profile,
                "--output",
                "json",
            ]
        )
        if not result.success:
            raise RuntimeError(result.parsed_error or result.stderr or "OCI compartment list failed")
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("OCI compartment list did not return valid JSON") from exc

        items = payload.get("data") or []
        compartments: list[OCICompartmentSummary] = []
        seen_ocids: set[str] = set()
        for item in items:
            name = item.get("name")
            ocid = item.get("id")
            if not isinstance(name, str) or not isinstance(ocid, str):
                continue
            if ocid in seen_ocids:
                continue
            seen_ocids.add(ocid)
            compartments.append(OCICompartmentSummary(name=name, ocid=ocid))
        return compartments

    def list_instances_by_compartment(self, compartment_ocid: str) -> list[OCIInstanceSummary]:
        result = self._run(
            [
                "compute",
                "instance",
                "list",
                "--compartment-id",
                compartment_ocid,
                "--all",
                "--query",
                'data[*].{nome:"display-name", id:"id", vcpus:"shape-config"."vcpus", memoria:"shape-config"."memory-in-gbs", criadoEm:"time-created"}',
                "--profile",
                self.settings.oci_cli_profile,
                "--output",
                "json",
            ]
        )
        if not result.success:
            raise RuntimeError(result.parsed_error or result.stderr or "OCI instance list failed")
        try:
            payload = json.loads(result.stdout or "[]")
        except json.JSONDecodeError as exc:
            raise RuntimeError("OCI instance list did not return valid JSON") from exc
        items = payload.get("data") if isinstance(payload, dict) else payload
        instances: list[OCIInstanceSummary] = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            name = item.get("nome")
            ocid = item.get("id")
            if not isinstance(name, str) or not isinstance(ocid, str):
                continue
            instances.append(
                OCIInstanceSummary(
                    name=name,
                    ocid=ocid,
                    vcpu=self._to_float(item.get("vcpus")),
                    memory_gbs=self._to_float(item.get("memoria")),
                    oci_created_at=self._parse_datetime(item.get("criadoEm")),
                )
            )
        return instances

    def get_instance_details(self, instance_ocid: str) -> OCIInstanceDetails:
        result = self._run(
            [
                "compute",
                "instance",
                "get",
                "--instance-id",
                instance_ocid,
                "--query",
                'data.{name:"display-name", id:id, compartmentId:"compartment-id", vcpus:"shape-config"."vcpus", memory:"shape-config"."memory-in-gbs", created:"time-created"}',
                "--profile",
                self.settings.oci_cli_profile,
                "--output",
                "json",
            ]
        )
        if not result.success:
            raise RuntimeError(result.parsed_error or result.stderr or "OCI instance lookup failed")
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("OCI instance lookup did not return valid JSON") from exc
        data = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(data, dict):
            raise RuntimeError("OCI instance lookup did not return instance data")

        name = data.get("name")
        ocid = data.get("id")
        compartment_ocid = data.get("compartmentId")
        if not isinstance(name, str) or not isinstance(ocid, str) or not isinstance(compartment_ocid, str):
            raise RuntimeError("OCI instance lookup returned incomplete instance data")

        return OCIInstanceDetails(
            name=name,
            ocid=ocid,
            compartment_ocid=compartment_ocid,
            vcpu=self._to_float(data.get("vcpus")),
            memory_gbs=self._to_float(data.get("memory")),
            oci_created_at=self._parse_datetime(data.get("created")),
        )

    def get_instance_vnic_id(self, instance_ocid: str) -> str | None:
        result = self._run(
            [
                "compute",
                "instance",
                "list-vnics",
                "--instance-id",
                instance_ocid,
                "--query",
                "data[0].id",
                "--raw-output",
                "--profile",
                self.settings.oci_cli_profile,
            ]
        )
        if not result.success:
            raise RuntimeError(result.parsed_error or result.stderr or "OCI instance VNIC lookup failed")
        output = (result.stdout or "").strip()
        if output in {"", "null", "None"}:
            return None
        return output

    def get_vnic_details(self, vnic_id: str) -> OCIVnicDetails:
        result = self._run(
            [
                "network",
                "vnic",
                "get",
                "--vnic-id",
                vnic_id,
                "--query",
                'data.{ipPublico:"public-ip", ipPrivado:"private-ip"}',
                "--raw-output",
                "--profile",
                self.settings.oci_cli_profile,
            ]
        )
        if not result.success:
            raise RuntimeError(result.parsed_error or result.stderr or "OCI VNIC details lookup failed")
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("OCI VNIC details did not return valid JSON") from exc
        if not isinstance(payload, dict):
            payload = {}
        return OCIVnicDetails(
            vnic_id=vnic_id,
            public_ip=payload.get("ipPublico") if isinstance(payload.get("ipPublico"), str) else None,
            private_ip=payload.get("ipPrivado") if isinstance(payload.get("ipPrivado"), str) else None,
        )

    @staticmethod
    def _to_float(value: object) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    @staticmethod
    def _parse_error(stderr: str | None) -> str | None:
        if not stderr:
            return None
        lowered = stderr.lower()
        if "could not find config file" in lowered or "config file" in lowered:
            return "oci_config_missing"
        if "no such file or directory" in lowered and ".pem" in lowered:
            return "oci_key_file_missing"
        if "profile" in lowered and "not found" in lowered:
            return "oci_profile_invalid"
        if "notauthenticated" in lowered or ("auth" in lowered and "invalid" in lowered):
            return "oci_credentials_invalid"
        if "notauthorizedornotfound" in lowered:
            return "oci_instance_not_found_or_forbidden"
        if "notauthorized" in lowered or "permission" in lowered:
            return "oci_permission_denied"
        return "oci_command_failed"


def get_oci_service() -> OCIService:
    return OCIService()
