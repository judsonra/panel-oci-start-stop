from datetime import datetime, timezone
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

import app.db.base  # noqa: E402,F401
from app.models.base import Base  # noqa: E402
from app.services.oci_cli import OCICompartmentSummary  # noqa: E402
from app.services.oci_cli import OCICommandResult  # noqa: E402
from app.services.oci_cli import OCIInstanceDetails, OCIInstanceSummary, OCIVnicDetails  # noqa: E402


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


class FakeOCIService:
    def __init__(self) -> None:
        self.mode = "success"
        self.compartments = [
            OCICompartmentSummary(name="Compartment A", ocid="ocid1.compartment.oc1..aaaa"),
            OCICompartmentSummary(name="Compartment B", ocid="ocid1.compartment.oc1..bbbb"),
        ]
        self.instances_by_compartment = {
            "ocid1.compartment.oc1..aaaa": [
                OCIInstanceSummary(
                    name="Instance A1",
                    ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
                    vcpu=2.0,
                    memory_gbs=12.0,
                    oci_created_at=datetime(2026, 3, 20, 10, 0, tzinfo=timezone.utc),
                )
            ],
            "ocid1.compartment.oc1..bbbb": [
                OCIInstanceSummary(
                    name="Instance B1",
                    ocid="ocid1.instance.oc1.sa-saopaulo-1.autob1",
                    vcpu=4.0,
                    memory_gbs=24.0,
                    oci_created_at=datetime(2026, 3, 21, 10, 0, tzinfo=timezone.utc),
                )
            ],
        }
        self.vnic_ids = {
            "ocid1.instance.oc1.sa-saopaulo-1.autoa1": "ocid1.vnic.oc1..aaaavnic",
            "ocid1.instance.oc1.sa-saopaulo-1.autob1": "ocid1.vnic.oc1..bbbbvnic",
        }
        self.instance_details = {
            "ocid1.instance.oc1.sa-saopaulo-1.autoa1": OCIInstanceDetails(
                name="Instance A1",
                ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
                compartment_ocid="ocid1.compartment.oc1..aaaa",
                vcpu=2.0,
                memory_gbs=12.0,
                oci_created_at=datetime(2026, 3, 20, 10, 0, tzinfo=timezone.utc),
            ),
            "ocid1.instance.oc1.sa-saopaulo-1.autob1": OCIInstanceDetails(
                name="Instance B1",
                ocid="ocid1.instance.oc1.sa-saopaulo-1.autob1",
                compartment_ocid="ocid1.compartment.oc1..bbbb",
                vcpu=4.0,
                memory_gbs=24.0,
                oci_created_at=datetime(2026, 3, 21, 10, 0, tzinfo=timezone.utc),
            ),
        }
        self.vnic_details = {
            "ocid1.vnic.oc1..aaaavnic": OCIVnicDetails(
                vnic_id="ocid1.vnic.oc1..aaaavnic", public_ip="129.1.1.1", private_ip="10.0.0.10"
            ),
            "ocid1.vnic.oc1..bbbbvnic": OCIVnicDetails(
                vnic_id="ocid1.vnic.oc1..bbbbvnic", public_ip=None, private_ip="10.0.1.10"
            ),
        }

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

    def list_compartments(self) -> list[OCICompartmentSummary]:
        return list(self.compartments)

    def list_instances_by_compartment(self, compartment_ocid: str) -> list[OCIInstanceSummary]:
        return list(self.instances_by_compartment.get(compartment_ocid, []))

    def get_instance_details(self, instance_ocid: str) -> OCIInstanceDetails:
        if instance_ocid not in self.instance_details:
            raise RuntimeError("instance_not_found")
        return self.instance_details[instance_ocid]

    def get_instance_vnic_id(self, instance_ocid: str) -> str | None:
        return self.vnic_ids.get(instance_ocid)

    def get_vnic_details(self, vnic_id: str) -> OCIVnicDetails:
        if vnic_id not in self.vnic_details:
            raise RuntimeError("vnic_not_found")
        return self.vnic_details[vnic_id]


fake_oci_service = FakeOCIService()


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    fake_oci_service.mode = "success"
    fake_oci_service.compartments = [
        OCICompartmentSummary(name="Compartment A", ocid="ocid1.compartment.oc1..aaaa"),
        OCICompartmentSummary(name="Compartment B", ocid="ocid1.compartment.oc1..bbbb"),
    ]
    fake_oci_service.instances_by_compartment = {
        "ocid1.compartment.oc1..aaaa": [
            OCIInstanceSummary(
                name="Instance A1",
                ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
                vcpu=2.0,
                memory_gbs=12.0,
                oci_created_at=datetime(2026, 3, 20, 10, 0, tzinfo=timezone.utc),
            )
        ],
        "ocid1.compartment.oc1..bbbb": [
            OCIInstanceSummary(
                name="Instance B1",
                ocid="ocid1.instance.oc1.sa-saopaulo-1.autob1",
                vcpu=4.0,
                memory_gbs=24.0,
                oci_created_at=datetime(2026, 3, 21, 10, 0, tzinfo=timezone.utc),
            )
        ],
    }
    fake_oci_service.vnic_ids = {
        "ocid1.instance.oc1.sa-saopaulo-1.autoa1": "ocid1.vnic.oc1..aaaavnic",
        "ocid1.instance.oc1.sa-saopaulo-1.autob1": "ocid1.vnic.oc1..bbbbvnic",
    }
    fake_oci_service.instance_details = {
        "ocid1.instance.oc1.sa-saopaulo-1.autoa1": OCIInstanceDetails(
            name="Instance A1",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autoa1",
            compartment_ocid="ocid1.compartment.oc1..aaaa",
            vcpu=2.0,
            memory_gbs=12.0,
            oci_created_at=datetime(2026, 3, 20, 10, 0, tzinfo=timezone.utc),
        ),
        "ocid1.instance.oc1.sa-saopaulo-1.autob1": OCIInstanceDetails(
            name="Instance B1",
            ocid="ocid1.instance.oc1.sa-saopaulo-1.autob1",
            compartment_ocid="ocid1.compartment.oc1..bbbb",
            vcpu=4.0,
            memory_gbs=24.0,
            oci_created_at=datetime(2026, 3, 21, 10, 0, tzinfo=timezone.utc),
        ),
    }
    fake_oci_service.vnic_details = {
        "ocid1.vnic.oc1..aaaavnic": OCIVnicDetails(
            vnic_id="ocid1.vnic.oc1..aaaavnic", public_ip="129.1.1.1", private_ip="10.0.0.10"
        ),
        "ocid1.vnic.oc1..bbbbvnic": OCIVnicDetails(
            vnic_id="ocid1.vnic.oc1..bbbbvnic", public_ip=None, private_ip="10.0.1.10"
        ),
    }
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def override_session() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
