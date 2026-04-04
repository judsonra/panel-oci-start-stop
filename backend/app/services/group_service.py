from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from fastapi import HTTPException, status

from app.models.compartment import Compartment
from app.models.group import Group
from app.models.instance import Instance
from app.repositories.group_repository import GroupRepository


def normalize_group_name(name: str) -> str:
    return " ".join(name.split()).casefold()


class GroupService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.groups = GroupRepository(session)

    def list_groups(self) -> list[Group]:
        return self.groups.list()

    def get_group(self, group_id: str) -> Group:
        group = self.groups.get(group_id)
        if group is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
        return group

    def create_group(self, name: str, instance_ids: list[str]) -> Group:
        normalized_name = normalize_group_name(name)
        if self.groups.get_by_normalized_name(normalized_name):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group name already registered")
        instances = self._load_instances(instance_ids)
        group = self.groups.create(name=" ".join(name.split()), normalized_name=normalized_name)
        group.instances = instances
        return self.groups.save(group)

    def update_group(self, group_id: str, name: str, instance_ids: list[str]) -> Group:
        group = self.get_group(group_id)
        normalized_name = normalize_group_name(name)
        conflict = self.groups.get_by_normalized_name(normalized_name)
        if conflict and conflict.id != group_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group name already registered")
        group.name = " ".join(name.split())
        group.normalized_name = normalized_name
        group.instances = self._load_instances(instance_ids)
        return self.groups.save(group)

    def delete_group(self, group_id: str) -> None:
        group = self.get_group(group_id)
        self.groups.delete(group)

    def list_tree(self) -> list[Compartment]:
        statement = (
            select(Compartment)
            .join(Compartment.instances)
            .options(selectinload(Compartment.instances))
            .distinct()
            .order_by(Compartment.name.asc())
        )
        compartments = list(self.session.scalars(statement).all())
        for compartment in compartments:
            compartment.instances = sorted(compartment.instances, key=lambda item: (item.name.casefold(), item.ocid.casefold()))
        return compartments

    def _load_instances(self, instance_ids: list[str]) -> list[Instance]:
        unique_ids = list(dict.fromkeys(instance_ids))
        statement = select(Instance).where(Instance.id.in_(unique_ids))
        instances = list(self.session.scalars(statement).all())
        if len(instances) != len(unique_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more instances were not found")
        return sorted(instances, key=lambda item: (item.name.casefold(), item.ocid.casefold()))
