from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.execution_log import ExecutionLog, ExecutionSource, ExecutionStatus
from app.models.instance import Instance
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.instance_repository import InstanceRepository
from app.schemas.instance import InstanceCreate, InstanceUpdate
from app.services.oci_cli import OCIService


class InstanceService:
    def __init__(self, session: Session, oci_service: OCIService) -> None:
        self.session = session
        self.instances = InstanceRepository(session)
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
        return self.instances.create(payload)

    def update_instance(self, instance_id: str, payload: InstanceUpdate) -> Instance:
        instance = self.get_instance(instance_id)
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
