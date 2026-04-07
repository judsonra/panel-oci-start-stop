from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import AppBaseModel


class AccessPermissionRead(AppBaseModel):
    id: str
    key: str
    label: str
    description: str | None = None


class AccessPermissionUpdate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    description: str | None = None


class AccessGroupRead(AppBaseModel):
    id: str
    name: str
    description: str | None = None
    is_active: bool
    permission_keys: list[str]
    member_count: int
    created_at: str
    updated_at: str


class AccessGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    is_active: bool = True
    permission_keys: list[str] = Field(default_factory=list)


class AccessGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    is_active: bool | None = None
    permission_keys: list[str] | None = None


class AccessUserRead(AppBaseModel):
    id: str
    email: str
    display_name: str | None = None
    is_active: bool
    is_superadmin: bool
    direct_permissions: list[str]
    group_ids: list[str]
    effective_permissions: list[str]
    created_at: str
    updated_at: str


class AccessUserCreate(BaseModel):
    email: EmailStr
    display_name: str | None = None
    is_active: bool = True
    is_superadmin: bool = False
    direct_permissions: list[str] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)


class AccessUserUpdate(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = None
    is_active: bool | None = None
    is_superadmin: bool | None = None
    direct_permissions: list[str] | None = None
    group_ids: list[str] | None = None
