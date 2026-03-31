from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text

from app.api.deps import get_compartment_service, get_instance_service, get_schedule_service
from app.core.security import CurrentUser, get_current_user
from app.repositories.execution_repository import ExecutionRepository
from app.schemas.compartment import CompartmentRead
from app.schemas.common import HealthResponse
from app.schemas.execution import ExecutionLogRead
from app.schemas.instance import InstanceActionResult, InstanceCreate, InstanceRead, InstanceUpdate
from app.schemas.schedule import ScheduleCreate, ScheduleRead, ScheduleUpdate
from app.services.compartment_service import CompartmentService
from app.services.instance_service import InstanceService
from app.services.oci_cli import OCIService, get_oci_service
from app.services.schedule_service import ScheduleService
from app.db.session import get_db_session
from sqlalchemy.orm import Session


router = APIRouter(prefix="/api")


def serialize_schedule(schedule) -> ScheduleRead:
    return ScheduleRead.model_validate(schedule).model_copy(update={"instance_name": schedule.instance.name if schedule.instance else None})


@router.get("/health", response_model=HealthResponse)
def health(
    session: Session = Depends(get_db_session),
    oci_service: OCIService = Depends(get_oci_service),
) -> HealthResponse:
    database_status = "ok"
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"

    oci_health = oci_service.health_status()
    cli_status = "ok" if oci_health.cli_available else "error"
    config_status = "ok" if oci_health.config_available else "error"
    overall_status = "ok" if database_status == "ok" and cli_status == "ok" and config_status == "ok" else "degraded"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        database=database_status,
        oci_cli=cli_status,
        oci_config=config_status,
        details={
            "oci_cli_path": oci_health.cli_path,
            "oci_cli_version": oci_health.cli_version,
            "oci_config_file": oci_health.config_file,
            "oci_key_file": oci_health.key_file,
            "oci_key_file_exists": str(oci_health.key_file_exists),
            "oci_error": oci_health.error,
        },
    )


@router.get("/instances", response_model=list[InstanceRead])
def list_instances(
    _: CurrentUser = Depends(get_current_user),
    service: InstanceService = Depends(get_instance_service),
) -> list[InstanceRead]:
    return [InstanceRead.model_validate(item) for item in service.list_instances()]


@router.get("/compartiments/list", response_model=list[CompartmentRead])
def list_compartments(
    _: CurrentUser = Depends(get_current_user),
    service: CompartmentService = Depends(get_compartment_service),
) -> list[CompartmentRead]:
    return [CompartmentRead.model_validate(item) for item in service.list_compartments()]


@router.get("/compartiments/listandupdate", response_model=list[CompartmentRead])
def list_and_update_compartments(
    _: CurrentUser = Depends(get_current_user),
    service: CompartmentService = Depends(get_compartment_service),
) -> list[CompartmentRead]:
    return [CompartmentRead.model_validate(item) for item in service.list_and_update()]


@router.post("/instances", response_model=InstanceRead, status_code=status.HTTP_201_CREATED)
def create_instance(
    payload: InstanceCreate,
    _: CurrentUser = Depends(get_current_user),
    service: InstanceService = Depends(get_instance_service),
) -> InstanceRead:
    return InstanceRead.model_validate(service.create_instance(payload))


@router.put("/instances/{instance_id}", response_model=InstanceRead)
def update_instance(
    instance_id: str,
    payload: InstanceUpdate,
    _: CurrentUser = Depends(get_current_user),
    service: InstanceService = Depends(get_instance_service),
) -> InstanceRead:
    return InstanceRead.model_validate(service.update_instance(instance_id, payload))


@router.delete("/instances/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instance(
    instance_id: str,
    _: CurrentUser = Depends(get_current_user),
    service: InstanceService = Depends(get_instance_service),
) -> Response:
    service.delete_instance(instance_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/instances/{instance_id}/start", response_model=ExecutionLogRead)
def start_instance(
    instance_id: str,
    _: CurrentUser = Depends(get_current_user),
    service: InstanceService = Depends(get_instance_service),
) -> ExecutionLogRead:
    return ExecutionLogRead.model_validate(service.start(instance_id))


@router.post("/instances/{instance_id}/stop", response_model=ExecutionLogRead)
def stop_instance(
    instance_id: str,
    _: CurrentUser = Depends(get_current_user),
    service: InstanceService = Depends(get_instance_service),
) -> ExecutionLogRead:
    return ExecutionLogRead.model_validate(service.stop(instance_id))


@router.get("/instances/{instance_id}/status", response_model=ExecutionLogRead)
def get_status(
    instance_id: str,
    _: CurrentUser = Depends(get_current_user),
    service: InstanceService = Depends(get_instance_service),
) -> ExecutionLogRead:
    execution = service.get_status(instance_id)
    return ExecutionLogRead.model_validate(execution).model_copy(update={"instance_state": execution.instance.last_known_state})


@router.get("/schedules", response_model=list[ScheduleRead])
def list_schedules(
    _: CurrentUser = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service),
) -> list[ScheduleRead]:
    return [serialize_schedule(item) for item in service.list_schedules()]


@router.post("/schedules", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreate,
    _: CurrentUser = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleRead:
    return serialize_schedule(service.create_schedule(payload))


@router.put("/schedules/{schedule_id}", response_model=ScheduleRead)
def update_schedule(
    schedule_id: str,
    payload: ScheduleUpdate,
    _: CurrentUser = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleRead:
    return serialize_schedule(service.update_schedule(schedule_id, payload))


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: str,
    _: CurrentUser = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service),
) -> Response:
    service.delete_schedule(schedule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/executions", response_model=list[ExecutionLogRead])
def list_executions(
    _: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> list[ExecutionLogRead]:
    repository = ExecutionRepository(session)
    executions: list[ExecutionLogRead] = []
    for item in repository.list():
        execution = ExecutionLogRead.model_validate(item)
        executions.append(
            execution.model_copy(
                update={"instance_name": item.instance.name if item.instance else item.instance_id}
            )
        )
    return executions
