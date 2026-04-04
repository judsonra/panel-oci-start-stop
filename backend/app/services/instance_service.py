from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.compartment import Compartment
from app.models.execution_log import ExecutionLog, ExecutionSource, ExecutionStatus
from app.models.instance import Instance
from app.repositories.compartment_repository import CompartmentRepository
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.instance_repository import InstanceRepository
from app.schemas.instance import InstanceCreate, InstanceUpdate
from app.services.oci_cli import OCIVnicDetails, OCIService


@dataclass
class ImportInstanceResult:
    ocid: str
    name: str
    status: str
    message: str | None
    vcpu: float | None
    memory_gbs: float | None
    vnic_id: str | None
    public_ip: str | None
    private_ip: str | None
    oci_created_at: datetime | None


@dataclass
class ImportCompartmentResult:
    compartment_ocid: str
    compartment_name: str
    total_instances: int
    created: int
    updated: int
    unchanged: int
    failed: int
    instances: list[ImportInstanceResult]


@dataclass
class ImportAllCompartmentsResult:
    total_compartments: int
    processed_compartments: int
    total_instances: int
    created: int
    updated: int
    unchanged: int
    failed: int
    compartments: list[ImportCompartmentResult]


class InstanceService:
    def __init__(self, session: Session, oci_service: OCIService) -> None:
        self.session = session
        self.instances = InstanceRepository(session)
        self.compartments = CompartmentRepository(session)
        self.executions = ExecutionRepository(session)
        self.oci_service = oci_service

    def list_instances(self) -> list[Instance]:
        return self.instances.list()

    def get_instance(self, instance_id: str) -> Instance:
        instance = self.instances.get(instance_id)
        if instance is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
        return instance

    def create_instance(self, payload: InstanceCreate) -> Instance:
        if self.instances.get_by_ocid(payload.ocid):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Instance OCID already registered")
        if payload.compartment_id and self.session.get(Compartment, payload.compartment_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Compartment not found")
        return self.instances.create(payload)

    def update_instance(self, instance_id: str, payload: InstanceUpdate) -> Instance:
        instance = self.get_instance(instance_id)
        if payload.compartment_id and self.session.get(Compartment, payload.compartment_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Compartment not found")
        return self.instances.update(instance, payload)

    def delete_instance(self, instance_id: str) -> None:
        instance = self.get_instance(instance_id)
        self.instances.delete(instance)

    def get_status(self, instance_id: str) -> ExecutionLog:
        instance = self.get_instance(instance_id)
        return self._execute_action(instance, "status", ExecutionSource.manual)

    def start(self, instance_id: str, source: ExecutionSource = ExecutionSource.manual) -> ExecutionLog:
        instance = self.get_instance(instance_id)
        return self._execute_action(instance, "start", source)

    def stop(self, instance_id: str, source: ExecutionSource = ExecutionSource.manual) -> ExecutionLog:
        instance = self.get_instance(instance_id)
        return self._execute_action(instance, "stop", source)

    def restart(self, instance_id: str, source: ExecutionSource = ExecutionSource.manual) -> ExecutionLog:
        instance = self.get_instance(instance_id)
        return self._execute_action(instance, "restart", source)

    def get_instance_vnic(self, instance_ocid: str) -> str | None:
        return self.oci_service.get_instance_vnic_id(instance_ocid)

    def get_vnic_details(self, vnic_id: str) -> OCIVnicDetails:
        return self.oci_service.get_vnic_details(vnic_id)

    def import_all_compartment_instances(self) -> ImportAllCompartmentsResult:
        compartments = [item for item in self.compartments.list() if item.active]
        results: list[ImportCompartmentResult] = []
        created = 0
        updated = 0
        unchanged = 0
        failed = 0
        total_instances = 0

        for compartment in compartments:
            compartment_result = self._import_compartment_instances(compartment)
            results.append(compartment_result)
            total_instances += compartment_result.total_instances
            created += compartment_result.created
            updated += compartment_result.updated
            unchanged += compartment_result.unchanged
            failed += compartment_result.failed

        return ImportAllCompartmentsResult(
            total_compartments=len(compartments),
            processed_compartments=len(results),
            total_instances=total_instances,
            created=created,
            updated=updated,
            unchanged=unchanged,
            failed=failed,
            compartments=results,
        )

    def _import_compartment_instances(self, compartment: Compartment) -> ImportCompartmentResult:
        try:
            oci_instances = self.oci_service.list_instances_by_compartment(compartment.ocid)
        except RuntimeError as exc:
            return ImportCompartmentResult(
                compartment_ocid=compartment.ocid,
                compartment_name=compartment.name,
                total_instances=0,
                created=0,
                updated=0,
                unchanged=0,
                failed=1,
                instances=[
                    ImportInstanceResult(
                        ocid="",
                        name=compartment.name,
                        status="failed",
                        message=str(exc),
                        vcpu=None,
                        memory_gbs=None,
                        vnic_id=None,
                        public_ip=None,
                        private_ip=None,
                        oci_created_at=None,
                    )
                ],
            )
        results: list[ImportInstanceResult] = []
        created = 0
        updated = 0
        unchanged = 0
        failed = 0

        for remote in oci_instances:
            try:
                vnic_id = self.oci_service.get_instance_vnic_id(remote.ocid)
                vnic_details = self.oci_service.get_vnic_details(vnic_id) if vnic_id else OCIVnicDetails(vnic_id="", public_ip=None, private_ip=None)
                status_name = self._upsert_imported_instance(
                    compartment.id,
                    remote.name,
                    remote.ocid,
                    remote.vcpu,
                    remote.memory_gbs,
                    vnic_id,
                    vnic_details.public_ip,
                    vnic_details.private_ip,
                    remote.oci_created_at,
                )
                if status_name == "created":
                    created += 1
                elif status_name == "updated":
                    updated += 1
                else:
                    unchanged += 1
                results.append(
                    ImportInstanceResult(
                        ocid=remote.ocid,
                        name=remote.name,
                        status=status_name,
                        message=None,
                        vcpu=remote.vcpu,
                        memory_gbs=remote.memory_gbs,
                        vnic_id=vnic_id,
                        public_ip=vnic_details.public_ip,
                        private_ip=vnic_details.private_ip,
                        oci_created_at=remote.oci_created_at,
                    )
                )
            except RuntimeError as exc:
                failed += 1
                results.append(
                    ImportInstanceResult(
                        ocid=remote.ocid,
                        name=remote.name,
                        status="failed",
                        message=str(exc),
                        vcpu=remote.vcpu,
                        memory_gbs=remote.memory_gbs,
                        vnic_id=None,
                        public_ip=None,
                        private_ip=None,
                        oci_created_at=remote.oci_created_at,
                    )
                )

        return ImportCompartmentResult(
            compartment_ocid=compartment.ocid,
            compartment_name=compartment.name,
            total_instances=len(oci_instances),
            created=created,
            updated=updated,
            unchanged=unchanged,
            failed=failed,
            instances=results,
        )

    def _upsert_imported_instance(
        self,
        compartment_id: str,
        name: str,
        ocid: str,
        vcpu: float | None,
        memory_gbs: float | None,
        vnic_id: str | None,
        public_ip: str | None,
        private_ip: str | None,
        oci_created_at: datetime | None,
    ) -> str:
        existing = self.instances.get_by_ocid(ocid)
        if existing is None:
            self.instances.create(
                InstanceCreate(
                    name=name,
                    ocid=ocid,
                    compartment_id=compartment_id,
                    description=None,
                    enabled=True,
                )
            )
            created_instance = self.instances.get_by_ocid(ocid)
            if created_instance is not None:
                self.instances.apply_updates(
                    created_instance,
                    {
                        "vcpu": vcpu,
                        "memory_gbs": memory_gbs,
                        "compartment_id": compartment_id,
                        "vnic_id": vnic_id,
                        "public_ip": public_ip,
                        "private_ip": private_ip,
                        "oci_created_at": oci_created_at,
                    },
                )
            return "created"

        _, changed = self.instances.apply_updates(
            existing,
            {
            "name": name,
            "compartment_id": compartment_id,
            "vcpu": vcpu,
                "memory_gbs": memory_gbs,
                "vnic_id": vnic_id,
                "public_ip": public_ip,
                "private_ip": private_ip,
                "oci_created_at": oci_created_at,
            },
        )
        return "updated" if changed else "unchanged"

    def _execute_action(self, instance: Instance, action: str, source: ExecutionSource) -> ExecutionLog:
        if not instance.enabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instance is disabled")
        started_at = datetime.now(timezone.utc)
        execution = ExecutionLog(
            instance_id=instance.id,
            action=action,
            source=source,
            status=ExecutionStatus.pending,
            started_at=started_at,
        )
        execution = self.executions.create(execution)
        if action == "start":
            command_result = self.oci_service.start_instance(instance.ocid)
        elif action == "stop":
            command_result = self.oci_service.stop_instance(instance.ocid)
        elif action == "restart":
            command_result = self.oci_service.restart_instance(instance.ocid)
        else:
            command_result = self.oci_service.get_status(instance.ocid)
        execution.status = ExecutionStatus.success if command_result.success else ExecutionStatus.failed
        execution.stdout_summary = command_result.stdout
        execution.stderr_summary = command_result.parsed_error or command_result.stderr
        execution.finished_at = datetime.now(timezone.utc)
        self.executions.update(execution)
        instance.last_known_state = command_result.state or instance.last_known_state
        self.session.add(instance)
        self.session.commit()
        return execution
