from sqlalchemy.orm import Session

from app.models.compartment import Compartment
from app.repositories.compartment_repository import CompartmentRepository
from app.services.oci_cli import OCIService


class CompartmentService:
    def __init__(self, session: Session, oci_service: OCIService) -> None:
        self.compartments = CompartmentRepository(session)
        self.oci_service = oci_service

    def list_compartments(self) -> list[Compartment]:
        return self.compartments.list()

    def list_and_update(self) -> list[Compartment]:
        remote_compartments = self.oci_service.list_compartments()
        active_ocids: set[str] = set()

        for item in remote_compartments:
            active_ocids.add(item.ocid)
            existing = self.compartments.get_by_ocid(item.ocid)
            if existing is None:
                self.compartments.create(name=item.name, ocid=item.ocid, active=True)
                continue
            if existing.name != item.name or existing.active is False:
                self.compartments.update(existing, name=item.name, active=True)

        self.compartments.deactivate_missing(active_ocids)
        return self.compartments.list()
