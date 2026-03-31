from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.services.compartment_service import CompartmentService
from app.services.instance_service import InstanceService
from app.services.oci_cli import OCIService, get_oci_service
from app.services.schedule_service import ScheduleService


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
