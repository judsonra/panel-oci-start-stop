from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compartment import Compartment


class CompartmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Compartment]:
        statement = select(Compartment).order_by(Compartment.name.asc(), Compartment.created_at.asc())
        return list(self.session.scalars(statement).all())

    def get_by_ocid(self, ocid: str) -> Compartment | None:
        return self.session.scalar(select(Compartment).where(Compartment.ocid == ocid))

    def create(self, *, name: str, ocid: str, active: bool = True) -> Compartment:
        compartment = Compartment(name=name, ocid=ocid, active=active)
        self.session.add(compartment)
        self.session.commit()
        self.session.refresh(compartment)
        return compartment

    def update(self, compartment: Compartment, *, name: str, active: bool) -> Compartment:
        compartment.name = name
        compartment.active = active
        self.session.add(compartment)
        self.session.commit()
        self.session.refresh(compartment)
        return compartment

    def deactivate_missing(self, active_ocids: set[str]) -> None:
        compartments = list(self.session.scalars(select(Compartment).where(Compartment.active.is_(True))).all())
        changed = False
        for compartment in compartments:
            if compartment.ocid not in active_ocids:
                compartment.active = False
                self.session.add(compartment)
                changed = True
        if changed:
            self.session.commit()
