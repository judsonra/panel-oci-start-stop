import logging
from collections.abc import Callable
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
from app.services.audit_service import AuditService
from app.services.oci_cli import OCIVnicDetails, OCIService

logger = logging.getLogger(__name__)


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


@dataclass
class ImportProgressSnapshot:
    total_compartments: int
    processed_compartments: int
    total_instances: int
    processed_instances: int
    created: int
    updated: int
    unchanged: int
    failed: int
    current_compartment_name: str | None
    current_instance_name: str | None


@dataclass
class InstanceImportPreview:
    name: str
    ocid: str
    vcpu: float | None
    memory_gbs: float | None
    vnic_id: str | None
    public_ip: str | None
    private_ip: str | None
    compartment_ocid: str
    compartment_name: str
    oci_created_at: datetime | None
    already_registered: bool


class InstanceService:
    def __init__(self, session: Session, oci_service: OCIService) -> None:
        self.session = session
        self.instances = InstanceRepository(session)
        self.compartments = CompartmentRepository(session)
        self.executions = ExecutionRepository(session)
        self.oci_service = oci_service
        self.audit = AuditService(session)

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

    def get_import_preview(self, instance_ocid: str) -> InstanceImportPreview:
        existing = self.instances.get_by_ocid(instance_ocid)
        if existing is not None:
            compartment = existing.compartment or (self.session.get(Compartment, existing.compartment_id) if existing.compartment_id else None)
            return InstanceImportPreview(
                name=existing.name,
                ocid=existing.ocid,
                vcpu=existing.vcpu,
                memory_gbs=existing.memory_gbs,
                vnic_id=existing.vnic_id,
                public_ip=existing.public_ip,
                private_ip=existing.private_ip,
                compartment_ocid=compartment.ocid if compartment is not None else existing.compartment_id or "",
                compartment_name=compartment.name if compartment is not None else "Compartimento não identificado",
                oci_created_at=existing.oci_created_at,
                already_registered=True,
            )

        try:
            details = self.oci_service.get_instance_details(instance_ocid)
            vnic_id = self.oci_service.get_instance_vnic_id(instance_ocid)
            vnic_details = self.oci_service.get_vnic_details(vnic_id) if vnic_id else OCIVnicDetails(vnic_id="", public_ip=None, private_ip=None)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        compartment = self._ensure_compartment_cached(details.compartment_ocid)
        return InstanceImportPreview(
            name=details.name,
            ocid=details.ocid,
            vcpu=details.vcpu,
            memory_gbs=details.memory_gbs,
            vnic_id=vnic_id,
            public_ip=vnic_details.public_ip,
            private_ip=vnic_details.private_ip,
            compartment_ocid=details.compartment_ocid,
            compartment_name=compartment.name,
            oci_created_at=details.oci_created_at,
            already_registered=False,
        )

    def import_instance(self, ocid: str, description: str | None, enabled: bool) -> Instance:
        if self.instances.get_by_ocid(ocid):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Instance OCID already registered")

        preview = self.get_import_preview(ocid)
        compartment = self._ensure_compartment_cached(preview.compartment_ocid, preview.compartment_name)
        created = self.instances.create(
            InstanceCreate(
                name=preview.name,
                ocid=preview.ocid,
                compartment_id=compartment.id,
                description=description,
                enabled=enabled,
            )
        )
        created, _ = self.instances.apply_updates(
            created,
            {
                "vcpu": preview.vcpu,
                "memory_gbs": preview.memory_gbs,
                "vnic_id": preview.vnic_id,
                "public_ip": preview.public_ip,
                "private_ip": preview.private_ip,
                "oci_created_at": preview.oci_created_at,
            },
        )
        return created

    def update_instance(self, instance_id: str, payload: InstanceUpdate) -> Instance:
        instance = self.get_instance(instance_id)
        if payload.compartment_id and self.session.get(Compartment, payload.compartment_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Compartment not found")
        return self.instances.update(instance, payload)

    def delete_instance(self, instance_id: str, *, actor_email: str | None = None, actor_user_id: str | None = None) -> None:
        instance = self.get_instance(instance_id)
        before_data = {
            "id": instance.id,
            "name": instance.name,
            "ocid": instance.ocid,
            "compartment_id": instance.compartment_id,
        }
        self.instances.delete(instance)
        self.audit.log_configuration_event(
            event_type="instance_deleted",
            entity_type="instance",
            entity_id=before_data["id"],
            actor_email=actor_email,
            actor_user_id=actor_user_id,
            summary=f"Instance {before_data['name']} deleted",
            before_data=before_data,
        )

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

    def import_all_compartment_instances(
        self,
        progress_callback: Callable[[ImportProgressSnapshot], None] | None = None,
        job_id: str | None = None,
    ) -> ImportAllCompartmentsResult:
        compartments = [item for item in self.compartments.list() if item.active]
        results: list[ImportCompartmentResult] = []
        processed_compartments = 0
        processed_instances = 0
        created = 0
        updated = 0
        unchanged = 0
        failed = 0
        total_instances = 0
        current_compartment_name: str | None = None
        current_instance_name: str | None = None

        def emit_progress() -> None:
            if progress_callback is None:
                return
            progress_callback(
                ImportProgressSnapshot(
                    total_compartments=len(compartments),
                    processed_compartments=processed_compartments,
                    total_instances=total_instances,
                    processed_instances=processed_instances,
                    created=created,
                    updated=updated,
                    unchanged=unchanged,
                    failed=failed,
                    current_compartment_name=current_compartment_name,
                    current_instance_name=current_instance_name,
                )
            )

        logger.info(
            "Automatic registration job started [job_id=%s total_compartments=%s]",
            job_id or "sync",
            len(compartments),
        )
        emit_progress()

        for compartment in compartments:
            current_compartment_name = compartment.name
            current_instance_name = None
            logger.info(
                "Automatic registration job processing compartment [job_id=%s compartment_ocid=%s compartment_name=%s]",
                job_id or "sync",
                compartment.ocid,
                compartment.name,
            )

            try:
                oci_instances = self.oci_service.list_instances_by_compartment(compartment.ocid)
                total_instances += len(oci_instances)
                logger.info(
                    "Automatic registration job listed compartment instances [job_id=%s compartment_ocid=%s compartment_name=%s total_instances=%s]",
                    job_id or "sync",
                    compartment.ocid,
                    compartment.name,
                    len(oci_instances),
                )
                emit_progress()
            except RuntimeError as exc:
                failed += 1
                processed_compartments += 1
                logger.info(
                    "Automatic registration job failed to list compartment instances [job_id=%s compartment_ocid=%s compartment_name=%s error=%s]",
                    job_id or "sync",
                    compartment.ocid,
                    compartment.name,
                    str(exc),
                )
                results.append(
                    ImportCompartmentResult(
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
                )
                emit_progress()
                continue

            compartment_results: list[ImportInstanceResult] = []
            compartment_created = 0
            compartment_updated = 0
            compartment_unchanged = 0
            compartment_failed = 0

            for remote in oci_instances:
                current_instance_name = remote.name
                logger.info(
                    "Automatic registration job processing instance [job_id=%s compartment_ocid=%s compartment_name=%s instance_ocid=%s instance_name=%s]",
                    job_id or "sync",
                    compartment.ocid,
                    compartment.name,
                    remote.ocid,
                    remote.name,
                )
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
                        compartment_created += 1
                    elif status_name == "updated":
                        updated += 1
                        compartment_updated += 1
                    else:
                        unchanged += 1
                        compartment_unchanged += 1
                    logger.info(
                        "Automatic registration job processed instance [job_id=%s compartment_ocid=%s compartment_name=%s instance_ocid=%s instance_name=%s status=%s created=%s updated=%s unchanged=%s failed=%s]",
                        job_id or "sync",
                        compartment.ocid,
                        compartment.name,
                        remote.ocid,
                        remote.name,
                        status_name,
                        created,
                        updated,
                        unchanged,
                        failed,
                    )
                    compartment_results.append(
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
                    compartment_failed += 1
                    logger.info(
                        "Automatic registration job failed instance [job_id=%s compartment_ocid=%s compartment_name=%s instance_ocid=%s instance_name=%s error=%s]",
                        job_id or "sync",
                        compartment.ocid,
                        compartment.name,
                        remote.ocid,
                        remote.name,
                        str(exc),
                    )
                    compartment_results.append(
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
                finally:
                    processed_instances += 1
                    emit_progress()

            current_instance_name = None
            processed_compartments += 1
            compartment_result = ImportCompartmentResult(
                compartment_ocid=compartment.ocid,
                compartment_name=compartment.name,
                total_instances=len(oci_instances),
                created=compartment_created,
                updated=compartment_updated,
                unchanged=compartment_unchanged,
                failed=compartment_failed,
                instances=compartment_results,
            )
            results.append(compartment_result)
            logger.info(
                "Automatic registration job finished compartment [job_id=%s compartment_ocid=%s compartment_name=%s total_instances=%s created=%s updated=%s unchanged=%s failed=%s]",
                job_id or "sync",
                compartment.ocid,
                compartment.name,
                compartment_result.total_instances,
                compartment_result.created,
                compartment_result.updated,
                compartment_result.unchanged,
                compartment_result.failed,
            )
            emit_progress()

        result = ImportAllCompartmentsResult(
            total_compartments=len(compartments),
            processed_compartments=processed_compartments,
            total_instances=total_instances,
            created=created,
            updated=updated,
            unchanged=unchanged,
            failed=failed,
            compartments=results,
        )
        logger.info(
            "Automatic registration job finished [job_id=%s processed_compartments=%s total_compartments=%s processed_instances=%s total_instances=%s created=%s updated=%s unchanged=%s failed=%s]",
            job_id or "sync",
            result.processed_compartments,
            result.total_compartments,
            processed_instances,
            result.total_instances,
            result.created,
            result.updated,
            result.unchanged,
            result.failed,
        )
        return result

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

    def _ensure_compartment_cached(self, compartment_ocid: str, known_name: str | None = None) -> Compartment:
        compartment = self.compartments.get_by_ocid(compartment_ocid)
        resolved_name = known_name or (compartment.name if compartment is not None else None)

        if resolved_name is None or (compartment is not None and compartment.active is False):
            resolved_name = self._lookup_compartment_name(compartment_ocid) or resolved_name

        if resolved_name is None:
            resolved_name = compartment_ocid

        if compartment is None:
            return self.compartments.create(name=resolved_name, ocid=compartment_ocid, active=True)

        if compartment.name != resolved_name or compartment.active is False:
            return self.compartments.update(compartment, name=resolved_name, active=True)

        return compartment

    def _lookup_compartment_name(self, compartment_ocid: str) -> str | None:
        try:
            compartments = self.oci_service.list_compartments()
        except RuntimeError:
            return None

        for item in compartments:
            if item.ocid == compartment_ocid:
                return item.name
        return None
