from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.group import Group


class GroupRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Group]:
        statement = select(Group).options(selectinload(Group.instances)).order_by(Group.name.asc(), Group.created_at.asc())
        return list(self.session.scalars(statement).all())

    def get(self, group_id: str) -> Group | None:
        statement = select(Group).options(selectinload(Group.instances)).where(Group.id == group_id)
        return self.session.scalar(statement)

    def get_by_normalized_name(self, normalized_name: str) -> Group | None:
        return self.session.scalar(select(Group).where(Group.normalized_name == normalized_name))

    def create(self, *, name: str, normalized_name: str) -> Group:
        group = Group(name=name, normalized_name=normalized_name)
        self.session.add(group)
        self.session.commit()
        self.session.refresh(group)
        return group

    def save(self, group: Group) -> Group:
        self.session.add(group)
        self.session.commit()
        self.session.refresh(group)
        return group

    def delete(self, group: Group) -> None:
        self.session.delete(group)
        self.session.commit()
