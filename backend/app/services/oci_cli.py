import json
import configparser
import os
import shutil
import subprocess
import time
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
                state = payload.get("data", {}).get("lifecycle-state")
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
