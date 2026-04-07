from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


access_user_permissions = Table(
    "access_user_permissions",
    Base.metadata,
    Column("user_id", String(), ForeignKey("access_users.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(), ForeignKey("access_permissions.id", ondelete="CASCADE"), primary_key=True),
)

access_group_permissions = Table(
    "access_group_permissions",
    Base.metadata,
    Column("group_id", String(), ForeignKey("access_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(), ForeignKey("access_permissions.id", ondelete="CASCADE"), primary_key=True),
)

access_group_members = Table(
    "access_group_members",
    Base.metadata,
    Column("group_id", String(), ForeignKey("access_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", String(), ForeignKey("access_users.id", ondelete="CASCADE"), primary_key=True),
)


class AccessPermission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "access_permissions"

    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)


class AccessGroup(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "access_groups"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    permissions = relationship("AccessPermission", secondary=access_group_permissions)
    members = relationship("AccessUser", secondary=access_group_members, back_populates="groups")


class AccessUser(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "access_users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    direct_permissions = relationship("AccessPermission", secondary=access_user_permissions)
    groups = relationship("AccessGroup", secondary=access_group_members, back_populates="members")
