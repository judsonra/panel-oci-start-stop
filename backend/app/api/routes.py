from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import text

from app.api.deps import (
    get_access_control_service,
    get_audit_service,
    get_auth_service,
    get_compartment_service,
    get_deskmanager_service,
    get_group_service,
    get_import_job_service,
    get_instance_service,
    get_schedule_service,
)
from app.core.security import CurrentUser, get_current_user, require_any_permission, require_permission
from app.repositories.execution_repository import ExecutionRepository
from app.schemas.access_control import (
    AccessGroupCreate,
    AccessGroupRead,
    AccessGroupUpdate,
    AccessPermissionRead,
    AccessPermissionUpdate,
    AccessUserCreate,
    AccessUserRead,
    AccessUserUpdate,
)
from app.schemas.audit import AuditAccessLogRead, AuditConfigurationLogRead
from app.schemas.auth import (
    AuthConfigRead,
    AuthTokenRead,
    CurrentUserRead,
    EntraExchangeRequest,
    LocalLoginRequest,
)
from app.schemas.compartment import CompartmentRead
from app.schemas.common import HealthResponse
from app.schemas.deskmanager import (
    DeskManagerCategoryRead,
    DeskManagerCreateTicketsRequest,
    DeskManagerCreateTicketsResponse,
    DeskManagerUserRead,
)
from app.schemas.execution import ExecutionLogRead
from app.schemas.group import GroupCreate, GroupRead, GroupTreeCompartmentRead, GroupTreeInstanceRead, GroupUpdate
from app.schemas.instance import (
    CompartmentInstancesImportRead,
    ImportInstancesJobCreateRead,
    ImportInstancesJobStatusRead,
    InstanceActionResult,
    InstanceCreate,
    InstanceImportCreate,
    InstanceImportPreviewRead,
    InstanceRead,
    InstanceStatusRefreshRead,
    InstanceUpdate,
    InstanceVnicRead,
    VnicDetailsRead,
)
from app.schemas.schedule import ScheduleCreate, ScheduleRead, ScheduleUpdate
from app.services.access_control_service import AccessControlService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.compartment_service import CompartmentService
from app.services.deskmanager_service import DeskManagerService
from app.services.group_service import GroupService
from app.services.import_job_service import ImportJobService
from app.services.instance_service import InstanceService
from app.services.oci_cli import OCIService, get_oci_service
from app.services.schedule_service import ScheduleService
from app.db.session import get_db_session
from sqlalchemy.orm import Session


router = APIRouter(prefix="/api")


def serialize_schedule(schedule) -> ScheduleRead:
    return ScheduleRead.model_validate(schedule).model_copy(
        update={
            "instance_name": schedule.instance.name if schedule.instance else None,
            "group_name": schedule.group.name if getattr(schedule, "group", None) else None,
        }
    )


def serialize_execution(execution) -> ExecutionLogRead:
    return ExecutionLogRead.model_validate(execution).model_copy(
        update={
            "instance_name": execution.instance.name if execution.instance else execution.instance_id,
            "instance_state": execution.instance.last_known_state if execution.instance else None,
        }
    )


def serialize_group(group) -> GroupRead:
    instances = sorted(group.instances, key=lambda item: (item.name.casefold(), item.ocid.casefold()))
    return GroupRead(
        id=group.id,
        name=group.name,
        instance_count=len(instances),
        instances=[
            {
                "id": item.id,
                "name": item.name,
                "ocid": item.ocid,
                "compartment_id": item.compartment_id,
            }
            for item in instances
        ],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


def serialize_deskmanager_user(user) -> DeskManagerUserRead:
    return DeskManagerUserRead(id=user.id, name=user.name)


def serialize_deskmanager_category(category) -> DeskManagerCategoryRead:
    return DeskManagerCategoryRead(id=category.id, name=category.name)


def serialize_access_permission(permission) -> AccessPermissionRead:
    return AccessPermissionRead.model_validate(permission)


def serialize_access_group(group) -> AccessGroupRead:
    return AccessGroupRead(
        id=group.id,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        permission_keys=sorted(item.key for item in group.permissions),
        member_count=len(group.members),
        created_at=group.created_at.isoformat(),
        updated_at=group.updated_at.isoformat(),
    )


def serialize_access_user(user, effective_permissions: list[str]) -> AccessUserRead:
    return AccessUserRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        is_superadmin=user.is_superadmin,
        direct_permissions=sorted(item.key for item in user.direct_permissions),
        group_ids=sorted(item.id for item in user.groups),
        effective_permissions=effective_permissions,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


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


@router.get("/auth/config", response_model=AuthConfigRead)
def get_auth_config(
    service: AuthService = Depends(get_auth_service),
) -> AuthConfigRead:
    return service.get_public_config()


@router.post("/auth/local/login", response_model=AuthTokenRead)
def login_local(
    payload: LocalLoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> AuthTokenRead:
    return service.login_local(
        email=payload.email,
        password=payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/auth/entra/exchange", response_model=AuthTokenRead)
async def exchange_entra_code(
    payload: EntraExchangeRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> AuthTokenRead:
    return await service.exchange_entra_code(
        code=payload.code,
        code_verifier=payload.code_verifier,
        redirect_uri=payload.redirect_uri,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/auth/me", response_model=CurrentUserRead)
def get_auth_me(
    current_user: CurrentUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> CurrentUserRead:
    return service.build_current_user_read(current_user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_auth(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> Response:
    service.create_logout_audit(
        current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/auth/page-access", status_code=status.HTTP_204_NO_CONTENT)
def register_page_access(
    payload: dict[str, str],
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    audit: AuditService = Depends(get_audit_service),
) -> Response:
    audit.log_access_event(
        event_type="page_access",
        auth_source=current_user.auth_source,
        email=current_user.email,
        user_id=current_user.access_user_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        path=payload.get("path"),
        method="NAVIGATE",
        status_code=status.HTTP_204_NO_CONTENT,
        message="Frontend page access",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/admin/permissions", response_model=list[AccessPermissionRead])
def list_access_permissions(
    _: CurrentUser = Depends(require_any_permission("admin.permissions.view", "admin.users.manage", "admin.access_groups.manage")),
    service: AccessControlService = Depends(get_access_control_service),
) -> list[AccessPermissionRead]:
    return [serialize_access_permission(item) for item in service.list_permissions()]


@router.put("/admin/permissions/{permission_id}", response_model=AccessPermissionRead)
def update_access_permission(
    permission_id: str,
    payload: AccessPermissionUpdate,
    current_user: CurrentUser = Depends(require_permission("admin.permissions.manage")),
    service: AccessControlService = Depends(get_access_control_service),
) -> AccessPermissionRead:
    permission = service.update_permission(permission_id, payload, actor_email=current_user.email, actor_user_id=current_user.access_user_id)
    return serialize_access_permission(permission)


@router.get("/admin/users", response_model=list[AccessUserRead])
def list_access_users(
    _: CurrentUser = Depends(require_permission("admin.users.view")),
    service: AccessControlService = Depends(get_access_control_service),
) -> list[AccessUserRead]:
    return [serialize_access_user(item, service.get_effective_permissions(item)) for item in service.list_users()]


@router.post("/admin/users", response_model=AccessUserRead, status_code=status.HTTP_201_CREATED)
def create_access_user(
    payload: AccessUserCreate,
    current_user: CurrentUser = Depends(require_permission("admin.users.manage")),
    service: AccessControlService = Depends(get_access_control_service),
) -> AccessUserRead:
    user = service.create_user(payload, actor_email=current_user.email, actor_user_id=current_user.access_user_id)
    return serialize_access_user(user, service.get_effective_permissions(user))


@router.put("/admin/users/{user_id}", response_model=AccessUserRead)
def update_access_user(
    user_id: str,
    payload: AccessUserUpdate,
    current_user: CurrentUser = Depends(require_permission("admin.users.manage")),
    service: AccessControlService = Depends(get_access_control_service),
) -> AccessUserRead:
    user = service.update_user(user_id, payload, actor_email=current_user.email, actor_user_id=current_user.access_user_id)
    return serialize_access_user(user, service.get_effective_permissions(user))


@router.get("/admin/groups", response_model=list[AccessGroupRead])
def list_access_groups(
    _: CurrentUser = Depends(require_permission("admin.access_groups.view")),
    service: AccessControlService = Depends(get_access_control_service),
) -> list[AccessGroupRead]:
    return [serialize_access_group(item) for item in service.list_groups()]


@router.post("/admin/groups", response_model=AccessGroupRead, status_code=status.HTTP_201_CREATED)
def create_access_group(
    payload: AccessGroupCreate,
    current_user: CurrentUser = Depends(require_permission("admin.access_groups.manage")),
    service: AccessControlService = Depends(get_access_control_service),
) -> AccessGroupRead:
    return serialize_access_group(service.create_group(payload, actor_email=current_user.email, actor_user_id=current_user.access_user_id))


@router.put("/admin/groups/{group_id}", response_model=AccessGroupRead)
def update_access_group(
    group_id: str,
    payload: AccessGroupUpdate,
    current_user: CurrentUser = Depends(require_permission("admin.access_groups.manage")),
    service: AccessControlService = Depends(get_access_control_service),
) -> AccessGroupRead:
    return serialize_access_group(service.update_group(group_id, payload, actor_email=current_user.email, actor_user_id=current_user.access_user_id))


@router.get("/audit/access", response_model=list[AuditAccessLogRead])
def list_audit_access(
    email: str | None = None,
    event_type: str | None = None,
    auth_source: str | None = None,
    query: str | None = None,
    _: CurrentUser = Depends(require_permission("audit.access.view")),
    service: AuditService = Depends(get_audit_service),
) -> list[AuditAccessLogRead]:
    return [AuditAccessLogRead.model_validate(item) for item in service.list_access_logs(email=email, event_type=event_type, auth_source=auth_source, query=query)]


@router.get("/audit/configurations", response_model=list[AuditConfigurationLogRead])
def list_audit_configurations(
    actor_email: str | None = None,
    event_type: str | None = None,
    entity_type: str | None = None,
    query: str | None = None,
    _: CurrentUser = Depends(require_permission("audit.settings.view")),
    service: AuditService = Depends(get_audit_service),
) -> list[AuditConfigurationLogRead]:
    return [
        AuditConfigurationLogRead.model_validate(item)
        for item in service.list_configuration_logs(actor_email=actor_email, event_type=event_type, entity_type=entity_type, query=query)
    ]


@router.get("/deskmanager/users", response_model=list[DeskManagerUserRead])
def list_deskmanager_users(
    _: CurrentUser = Depends(require_permission("deskmanager.view")),
    service: DeskManagerService = Depends(get_deskmanager_service),
) -> list[DeskManagerUserRead]:
    return [serialize_deskmanager_user(item) for item in service.list_users()]


@router.get("/deskmanager/categories", response_model=list[DeskManagerCategoryRead])
def list_deskmanager_categories(
    search: str | None = None,
    _: CurrentUser = Depends(require_permission("deskmanager.view")),
    service: DeskManagerService = Depends(get_deskmanager_service),
) -> list[DeskManagerCategoryRead]:
    return [serialize_deskmanager_category(item) for item in service.list_categories(search)]


@router.post("/deskmanager/criarchamado", response_model=DeskManagerCreateTicketsResponse)
def create_deskmanager_tickets(
    payload: DeskManagerCreateTicketsRequest,
    _: CurrentUser = Depends(require_permission("deskmanager.create_ticket")),
    service: DeskManagerService = Depends(get_deskmanager_service),
) -> DeskManagerCreateTicketsResponse:
    return service.create_tickets(payload.items)


@router.get("/instances", response_model=list[InstanceRead])
def list_instances(
    _: CurrentUser = Depends(require_permission("instances.view")),
    service: InstanceService = Depends(get_instance_service),
) -> list[InstanceRead]:
    return [InstanceRead.model_validate(item) for item in service.list_instances()]


@router.get("/groups", response_model=list[GroupRead])
def list_groups(
    _: CurrentUser = Depends(require_permission("groups.view")),
    service: GroupService = Depends(get_group_service),
) -> list[GroupRead]:
    return [serialize_group(item) for item in service.list_groups()]


@router.get("/groups/tree", response_model=list[GroupTreeCompartmentRead])
def list_group_tree(
    _: CurrentUser = Depends(require_permission("groups.view")),
    service: GroupService = Depends(get_group_service),
) -> list[GroupTreeCompartmentRead]:
    compartments = service.list_tree()
    return [
        GroupTreeCompartmentRead(
            id=compartment.id,
            name=compartment.name,
            instances=[
                GroupTreeInstanceRead(id=item.id, name=item.name, ocid=item.ocid)
                for item in compartment.instances
            ],
        )
        for compartment in compartments
    ]


@router.get("/groups/{group_id}", response_model=GroupRead)
def get_group(
    group_id: str,
    _: CurrentUser = Depends(require_permission("groups.view")),
    service: GroupService = Depends(get_group_service),
) -> GroupRead:
    return serialize_group(service.get_group(group_id))


@router.post("/groups", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    _: CurrentUser = Depends(require_permission("groups.manage")),
    service: GroupService = Depends(get_group_service),
) -> GroupRead:
    return serialize_group(service.create_group(payload.name, payload.instance_ids))


@router.put("/groups/{group_id}", response_model=GroupRead)
def update_group(
    group_id: str,
    payload: GroupUpdate,
    _: CurrentUser = Depends(require_permission("groups.manage")),
    service: GroupService = Depends(get_group_service),
) -> GroupRead:
    return serialize_group(service.update_group(group_id, payload.name, payload.instance_ids))


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: str,
    current_user: CurrentUser = Depends(require_permission("groups.manage")),
    service: GroupService = Depends(get_group_service),
) -> Response:
    service.delete_group(group_id, actor_email=current_user.email, actor_user_id=current_user.access_user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/compartiments/list", response_model=list[CompartmentRead])
def list_compartments(
    _: CurrentUser = Depends(require_permission("compartments.view")),
    service: CompartmentService = Depends(get_compartment_service),
) -> list[CompartmentRead]:
    return [CompartmentRead.model_validate(item) for item in service.list_compartments()]


@router.get("/compartiments/listandupdate", response_model=list[CompartmentRead])
def list_and_update_compartments(
    _: CurrentUser = Depends(require_permission("compartments.manage")),
    service: CompartmentService = Depends(get_compartment_service),
) -> list[CompartmentRead]:
    return [CompartmentRead.model_validate(item) for item in service.list_and_update()]


@router.get("/compartiments/instancesall", response_model=CompartmentInstancesImportRead)
def import_all_compartment_instances(
    _: CurrentUser = Depends(require_permission("compartments.manage")),
    service: InstanceService = Depends(get_instance_service),
) -> CompartmentInstancesImportRead:
    return CompartmentInstancesImportRead(**asdict(service.import_all_compartment_instances()))


@router.post("/compartiments/instancesall/jobs", response_model=ImportInstancesJobCreateRead, status_code=status.HTTP_202_ACCEPTED)
def create_import_all_compartment_instances_job(
    _: CurrentUser = Depends(require_permission("compartments.manage")),
    service: ImportJobService = Depends(get_import_job_service),
) -> ImportInstancesJobCreateRead:
    job = service.start_import_all_compartments_job()
    return ImportInstancesJobCreateRead(job_id=job.job_id, status=job.status, started_at=job.started_at)


@router.get("/compartiments/instancesall/jobs/{job_id}", response_model=ImportInstancesJobStatusRead)
def get_import_all_compartment_instances_job(
    job_id: str,
    _: CurrentUser = Depends(require_permission("compartments.manage")),
    service: ImportJobService = Depends(get_import_job_service),
) -> ImportInstancesJobStatusRead:
    try:
        job = service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found") from exc

    return ImportInstancesJobStatusRead(
        job_id=job.job_id,
        status=job.status,
        started_at=job.started_at,
        finished_at=job.finished_at,
        total_compartments=job.total_compartments,
        processed_compartments=job.processed_compartments,
        total_instances=job.total_instances,
        processed_instances=job.processed_instances,
        created=job.created,
        updated=job.updated,
        unchanged=job.unchanged,
        failed=job.failed,
        current_compartment_name=job.current_compartment_name,
        current_instance_name=job.current_instance_name,
        result=CompartmentInstancesImportRead(**asdict(job.result)) if job.result is not None else None,
        error=job.error,
    )


@router.get("/compartiments/instances/{instance_ocid}/vnic", response_model=InstanceVnicRead)
def get_instance_vnic(
    instance_ocid: str,
    _: CurrentUser = Depends(require_permission("compartments.view")),
    service: InstanceService = Depends(get_instance_service),
) -> InstanceVnicRead:
    return InstanceVnicRead(instance_ocid=instance_ocid, vnic_id=service.get_instance_vnic(instance_ocid))


@router.get("/compartiments/vnics/{vnic_id}", response_model=VnicDetailsRead)
def get_vnic_details(
    vnic_id: str,
    _: CurrentUser = Depends(require_permission("compartments.view")),
    service: InstanceService = Depends(get_instance_service),
) -> VnicDetailsRead:
    details = service.get_vnic_details(vnic_id)
    return VnicDetailsRead(vnic_id=details.vnic_id, public_ip=details.public_ip, private_ip=details.private_ip)


@router.post("/instances", response_model=InstanceRead, status_code=status.HTTP_201_CREATED)
def create_instance(
    payload: InstanceCreate,
    _: CurrentUser = Depends(require_permission("instances.manage")),
    service: InstanceService = Depends(get_instance_service),
) -> InstanceRead:
    return InstanceRead.model_validate(service.create_instance(payload))


@router.get("/instances/import-preview/{instance_ocid}", response_model=InstanceImportPreviewRead)
def get_instance_import_preview(
    instance_ocid: str,
    _: CurrentUser = Depends(require_permission("instances.manage")),
    service: InstanceService = Depends(get_instance_service),
) -> InstanceImportPreviewRead:
    return InstanceImportPreviewRead(**asdict(service.get_import_preview(instance_ocid)))


@router.post("/instances/import", response_model=InstanceRead, status_code=status.HTTP_201_CREATED)
def import_instance(
    payload: InstanceImportCreate,
    _: CurrentUser = Depends(require_permission("instances.manage")),
    service: InstanceService = Depends(get_instance_service),
) -> InstanceRead:
    return InstanceRead.model_validate(service.import_instance(payload.ocid, payload.description, payload.enabled))


@router.put("/instances/{instance_id}", response_model=InstanceRead)
def update_instance(
    instance_id: str,
    payload: InstanceUpdate,
    _: CurrentUser = Depends(require_permission("instances.manage")),
    service: InstanceService = Depends(get_instance_service),
) -> InstanceRead:
    return InstanceRead.model_validate(service.update_instance(instance_id, payload))


@router.delete("/instances/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instance(
    instance_id: str,
    current_user: CurrentUser = Depends(require_permission("instances.manage")),
    service: InstanceService = Depends(get_instance_service),
) -> Response:
    service.delete_instance(instance_id, actor_email=current_user.email, actor_user_id=current_user.access_user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/instances/{instance_id}/start", response_model=ExecutionLogRead)
def start_instance(
    instance_id: str,
    _: CurrentUser = Depends(require_permission("instances.manage")),
    service: InstanceService = Depends(get_instance_service),
) -> ExecutionLogRead:
    return serialize_execution(service.start(instance_id))


@router.post("/instances/{instance_id}/stop", response_model=ExecutionLogRead)
def stop_instance(
    instance_id: str,
    _: CurrentUser = Depends(require_permission("instances.manage")),
    service: InstanceService = Depends(get_instance_service),
) -> ExecutionLogRead:
    return serialize_execution(service.stop(instance_id))


@router.get("/instances/{instance_id}/status", response_model=ExecutionLogRead)
def get_status(
    instance_id: str,
    _: CurrentUser = Depends(require_permission("instances.view")),
    service: InstanceService = Depends(get_instance_service),
) -> ExecutionLogRead:
    return serialize_execution(service.get_status(instance_id))


@router.post("/instances/status-refresh", response_model=InstanceStatusRefreshRead)
def refresh_instance_statuses(
    _: CurrentUser = Depends(require_permission("instances.view")),
    service: InstanceService = Depends(get_instance_service),
) -> InstanceStatusRefreshRead:
    return InstanceStatusRefreshRead(**asdict(service.refresh_statuses_by_compartment()))


@router.get("/schedules", response_model=list[ScheduleRead])
def list_schedules(
    _: CurrentUser = Depends(require_permission("schedules.view")),
    service: ScheduleService = Depends(get_schedule_service),
) -> list[ScheduleRead]:
    return [serialize_schedule(item) for item in service.list_schedules()]


@router.post("/schedules", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreate,
    current_user: CurrentUser = Depends(require_permission("schedules.manage")),
    service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleRead:
    return serialize_schedule(service.create_schedule(payload, actor_email=current_user.email, actor_user_id=current_user.access_user_id))


@router.put("/schedules/{schedule_id}", response_model=ScheduleRead)
def update_schedule(
    schedule_id: str,
    payload: ScheduleUpdate,
    current_user: CurrentUser = Depends(require_permission("schedules.manage")),
    service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleRead:
    return serialize_schedule(service.update_schedule(schedule_id, payload, actor_email=current_user.email, actor_user_id=current_user.access_user_id))


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: str,
    current_user: CurrentUser = Depends(require_permission("schedules.manage")),
    service: ScheduleService = Depends(get_schedule_service),
) -> Response:
    service.delete_schedule(schedule_id, actor_email=current_user.email, actor_user_id=current_user.access_user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/executions", response_model=list[ExecutionLogRead])
def list_executions(
    _: CurrentUser = Depends(require_permission("audit.executions.view")),
    session: Session = Depends(get_db_session),
) -> list[ExecutionLogRead]:
    repository = ExecutionRepository(session)
    executions: list[ExecutionLogRead] = []
    for item in repository.list():
        executions.append(serialize_execution(item))
    return executions


@router.get("/audit/executions", response_model=list[ExecutionLogRead])
def list_audit_executions(
    current_user: CurrentUser = Depends(require_permission("audit.executions.view")),
    session: Session = Depends(get_db_session),
) -> list[ExecutionLogRead]:
    return list_executions(current_user, session)
