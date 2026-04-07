from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.core.config import Settings, get_settings
from app.services.compartment_service import CompartmentService
from app.services.access_control_service import AccessControlService
from app.services.audit_service import AuditService
from app.services.deskmanager_service import DeskManagerService
from app.services.group_service import GroupService
from app.services.import_job_service import ImportJobService
from app.services.instance_service import InstanceService
from app.services.auth_service import AuthService
from app.services.oci_cli import OCIService, get_oci_service
from app.services.schedule_service import ScheduleService

import_job_service = ImportJobService()


def get_instance_service(
    session: Session = Depends(get_db_session),
    oci_service: OCIService = Depends(get_oci_service),
) -> InstanceService:
    return InstanceService(session, oci_service)


def get_schedule_service(
    session: Session = Depends(get_db_session),
    oci_service: OCIService = Depends(get_oci_service),
) -> ScheduleService:
    instance_service = InstanceService(session, oci_service)
    return ScheduleService(session, instance_service)


def get_compartment_service(
    session: Session = Depends(get_db_session),
    oci_service: OCIService = Depends(get_oci_service),
) -> CompartmentService:
    return CompartmentService(session, oci_service)


def get_group_service(
    session: Session = Depends(get_db_session),
) -> GroupService:
    return GroupService(session)


def get_access_control_service(
    session: Session = Depends(get_db_session),
) -> AccessControlService:
    return AccessControlService(session)


def get_audit_service(
    session: Session = Depends(get_db_session),
) -> AuditService:
    return AuditService(session)


def get_auth_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(session, settings)


def get_deskmanager_service(
    session: Session = Depends(get_db_session),
) -> DeskManagerService:
    return DeskManagerService(session)


def get_import_job_service() -> ImportJobService:
    return import_job_service
