from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.deskmanager_category import DeskManagerCategory
from app.models.deskmanager_user import DeskManagerUser


class DeskManagerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_users(self) -> list[DeskManagerUser]:
        statement = select(DeskManagerUser).order_by(DeskManagerUser.name.asc(), DeskManagerUser.id.asc())
        return list(self.session.scalars(statement).all())

    def list_categories(self, search: str | None = None) -> list[DeskManagerCategory]:
        statement = select(DeskManagerCategory)
        normalized_search = (search or "").strip()
        if normalized_search:
            statement = statement.where(DeskManagerCategory.name.ilike(f"%{normalized_search}%"))
        statement = statement.order_by(DeskManagerCategory.name.asc(), DeskManagerCategory.id.asc())
        return list(self.session.scalars(statement).all())

    def get_users_by_ids(self, user_ids: list[str]) -> list[DeskManagerUser]:
        if not user_ids:
            return []
        statement = select(DeskManagerUser).where(DeskManagerUser.id.in_(user_ids))
        return list(self.session.scalars(statement).all())

    def get_categories_by_ids(self, category_ids: list[str]) -> list[DeskManagerCategory]:
        if not category_ids:
            return []
        statement = select(DeskManagerCategory).where(DeskManagerCategory.id.in_(category_ids))
        return list(self.session.scalars(statement).all())
