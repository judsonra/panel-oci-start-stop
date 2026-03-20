import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["AUTH_ENABLED"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.models.base import Base  # noqa: E402
from app.services.oci_cli import OCICommandResult  # noqa: E402


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


class FakeOCIService:
    def __init__(self) -> None:
        self.mode = "success"

    def start_instance(self, _: str) -> OCICommandResult:
        if self.mode == "failure":
            return OCICommandResult(
                state=None,
                stdout=None,
                stderr="boom",
                return_code=1,
                command=["oci", "compute", "instance", "action"],
                duration_ms=1,
                parsed_error="oci_command_failed",
            )
        return OCICommandResult(
            state="RUNNING",
            stdout="started",
            stderr=None,
            return_code=0,
            command=["oci", "compute", "instance", "action"],
            duration_ms=1,
        )

    def stop_instance(self, _: str) -> OCICommandResult:
        if self.mode == "failure":
            return OCICommandResult(
                state=None,
                stdout=None,
                stderr="boom",
                return_code=1,
                command=["oci", "compute", "instance", "action"],
                duration_ms=1,
                parsed_error="oci_command_failed",
            )
        return OCICommandResult(
            state="STOPPED",
            stdout="stopped",
            stderr=None,
            return_code=0,
            command=["oci", "compute", "instance", "action"],
            duration_ms=1,
        )

    def restart_instance(self, _: str) -> OCICommandResult:
        if self.mode == "failure":
            return OCICommandResult(
                state=None,
                stdout=None,
                stderr="boom",
                return_code=1,
                command=["oci", "compute", "instance", "action"],
                duration_ms=1,
                parsed_error="oci_command_failed",
            )
        return OCICommandResult(
            state="RUNNING",
            stdout="restarted",
            stderr=None,
            return_code=0,
            command=["oci", "compute", "instance", "action"],
            duration_ms=1,
        )

    def get_status(self, _: str) -> OCICommandResult:
        return OCICommandResult(
            state="RUNNING",
            stdout='{"data":{"lifecycle-state":"RUNNING"}}',
            stderr=None,
            return_code=0,
            command=["oci", "compute", "instance", "get"],
            duration_ms=1,
        )


fake_oci_service = FakeOCIService()


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    fake_oci_service.mode = "success"
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def override_session() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
