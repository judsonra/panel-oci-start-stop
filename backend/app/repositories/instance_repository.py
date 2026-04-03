from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.instance import Instance
from app.schemas.instance import InstanceCreate, InstanceUpdate


class InstanceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Instance]:
        return list(self.session.scalars(select(Instance).order_by(Instance.created_at.desc())).all())

    def get(self, instance_id: str) -> Instance | None:
        return self.session.get(Instance, instance_id)

    def get_by_ocid(self, ocid: str) -> Instance | None:
        return self.session.scalar(select(Instance).where(Instance.ocid == ocid))

    def create(self, payload: InstanceCreate) -> Instance:
        instance = Instance(**payload.model_dump())
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def update(self, instance: Instance, payload: InstanceUpdate) -> Instance:
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(instance, field, value)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def apply_updates(self, instance: Instance, updates: Mapping[str, object]) -> tuple[Instance, bool]:
        changed = False
        for field, value in updates.items():
            if getattr(instance, field) != value:
                setattr(instance, field, value)
                changed = True
        if changed:
            self.session.add(instance)
            self.session.commit()
            self.session.refresh(instance)
        return instance, changed

    def delete(self, instance: Instance) -> None:
        self.session.delete(instance)
        self.session.commit()
