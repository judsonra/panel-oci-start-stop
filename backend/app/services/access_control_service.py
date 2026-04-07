from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.access_control import AccessGroup, AccessPermission, AccessUser
from app.schemas.access_control import AccessGroupCreate, AccessGroupUpdate, AccessPermissionUpdate, AccessUserCreate, AccessUserUpdate
from app.services.access_catalog import ACCESS_PERMISSION_CATALOG
from app.services.audit_service import AuditService


class AccessControlService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.audit = AuditService(session)

    def list_permissions(self) -> list[AccessPermission]:
        return list(self.session.scalars(select(AccessPermission).order_by(AccessPermission.key.asc())).all())

    def get_permission(self, permission_id: str) -> AccessPermission:
        permission = self.session.get(AccessPermission, permission_id)
        if permission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access permission not found")
        return permission

    def update_permission(
        self,
        permission_id: str,
        payload: AccessPermissionUpdate,
        *,
        actor_email: str | None,
        actor_user_id: str | None,
    ) -> AccessPermission:
        permission = self.get_permission(permission_id)
        before_data = self.serialize_permission(permission)
        permission.label = payload.label.strip()
        permission.description = payload.description.strip() if payload.description else None
        self.session.add(permission)
        self.session.commit()
        self.session.refresh(permission)
        self.audit.log_configuration_event(
            event_type="permission_updated",
            entity_type="access_permission",
            entity_id=permission.id,
            actor_email=actor_email,
            actor_user_id=actor_user_id,
            summary=f"Access permission {permission.key} updated",
            before_data=before_data,
            after_data=self.serialize_permission(permission),
        )
        return permission

    def list_users(self) -> list[AccessUser]:
        statement = (
            select(AccessUser)
            .options(selectinload(AccessUser.direct_permissions), selectinload(AccessUser.groups).selectinload(AccessGroup.permissions))
            .order_by(AccessUser.email.asc())
        )
        return list(self.session.scalars(statement).all())

    def get_user(self, user_id: str) -> AccessUser:
        statement = (
            select(AccessUser)
            .options(selectinload(AccessUser.direct_permissions), selectinload(AccessUser.groups).selectinload(AccessGroup.permissions))
            .where(AccessUser.id == user_id)
        )
        user = self.session.scalar(statement)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access user not found")
        return user

    def get_user_by_email(self, email: str) -> AccessUser | None:
        statement = (
            select(AccessUser)
            .options(selectinload(AccessUser.direct_permissions), selectinload(AccessUser.groups).selectinload(AccessGroup.permissions))
            .where(AccessUser.email == email.strip().casefold())
        )
        return self.session.scalar(statement)

    def list_groups(self) -> list[AccessGroup]:
        statement = select(AccessGroup).options(selectinload(AccessGroup.permissions), selectinload(AccessGroup.members)).order_by(AccessGroup.name.asc())
        return list(self.session.scalars(statement).all())

    def get_group(self, group_id: str) -> AccessGroup:
        statement = select(AccessGroup).options(selectinload(AccessGroup.permissions), selectinload(AccessGroup.members)).where(AccessGroup.id == group_id)
        group = self.session.scalar(statement)
        if group is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access group not found")
        return group

    def create_user(self, payload: AccessUserCreate, *, actor_email: str | None, actor_user_id: str | None) -> AccessUser:
        normalized_email = payload.email.strip().casefold()
        if self.get_user_by_email(normalized_email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access user email already registered")
        user = AccessUser(
            email=normalized_email,
            display_name=payload.display_name.strip() if payload.display_name else None,
            is_active=payload.is_active,
            is_superadmin=payload.is_superadmin,
        )
        user.direct_permissions = self._resolve_permissions(payload.direct_permissions)
        user.groups = self._resolve_groups(payload.group_ids)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        self.audit.log_configuration_event(
            event_type="user_created",
            entity_type="access_user",
            entity_id=user.id,
            actor_email=actor_email,
            actor_user_id=actor_user_id,
            summary=f"Access user {user.email} created",
            after_data=self.serialize_user(user),
        )
        return self.get_user(user.id)

    def update_user(self, user_id: str, payload: AccessUserUpdate, *, actor_email: str | None, actor_user_id: str | None) -> AccessUser:
        user = self.get_user(user_id)
        before_data = self.serialize_user(user)
        if payload.email is not None:
            normalized_email = payload.email.strip().casefold()
            conflict = self.get_user_by_email(normalized_email)
            if conflict and conflict.id != user.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access user email already registered")
            user.email = normalized_email
        if payload.display_name is not None:
            user.display_name = payload.display_name.strip() or None
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.is_superadmin is not None:
            user.is_superadmin = payload.is_superadmin
        if payload.direct_permissions is not None:
            user.direct_permissions = self._resolve_permissions(payload.direct_permissions)
        if payload.group_ids is not None:
            user.groups = self._resolve_groups(payload.group_ids)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        user = self.get_user(user.id)
        self.audit.log_configuration_event(
            event_type="user_updated",
            entity_type="access_user",
            entity_id=user.id,
            actor_email=actor_email,
            actor_user_id=actor_user_id,
            summary=f"Access user {user.email} updated",
            before_data=before_data,
            after_data=self.serialize_user(user),
        )
        return user

    def create_group(self, payload: AccessGroupCreate, *, actor_email: str | None, actor_user_id: str | None) -> AccessGroup:
        normalized_name = " ".join(payload.name.split())
        conflict = self.session.scalar(select(AccessGroup).where(AccessGroup.name == normalized_name))
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access group name already registered")
        group = AccessGroup(name=normalized_name, description=payload.description, is_active=payload.is_active)
        group.permissions = self._resolve_permissions(payload.permission_keys)
        self.session.add(group)
        self.session.commit()
        self.session.refresh(group)
        group = self.get_group(group.id)
        self.audit.log_configuration_event(
            event_type="group_created",
            entity_type="access_group",
            entity_id=group.id,
            actor_email=actor_email,
            actor_user_id=actor_user_id,
            summary=f"Access group {group.name} created",
            after_data=self.serialize_group(group),
        )
        return group

    def update_group(self, group_id: str, payload: AccessGroupUpdate, *, actor_email: str | None, actor_user_id: str | None) -> AccessGroup:
        group = self.get_group(group_id)
        before_data = self.serialize_group(group)
        if payload.name is not None:
            normalized_name = " ".join(payload.name.split())
            conflict = self.session.scalar(select(AccessGroup).where(AccessGroup.name == normalized_name))
            if conflict and conflict.id != group.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access group name already registered")
            group.name = normalized_name
        if payload.description is not None:
            group.description = payload.description
        if payload.is_active is not None:
            group.is_active = payload.is_active
        if payload.permission_keys is not None:
            group.permissions = self._resolve_permissions(payload.permission_keys)
        self.session.add(group)
        self.session.commit()
        self.session.refresh(group)
        group = self.get_group(group.id)
        self.audit.log_configuration_event(
            event_type="group_updated",
            entity_type="access_group",
            entity_id=group.id,
            actor_email=actor_email,
            actor_user_id=actor_user_id,
            summary=f"Access group {group.name} updated",
            before_data=before_data,
            after_data=self.serialize_group(group),
        )
        return group

    def get_effective_permissions(self, user: AccessUser | None) -> list[str]:
        if user is None or not user.is_active:
            return []
        if user.is_superadmin:
            return [item[0] for item in ACCESS_PERMISSION_CATALOG]
        keys = {permission.key for permission in user.direct_permissions}
        for group in user.groups:
            if not group.is_active:
                continue
            keys.update(permission.key for permission in group.permissions)
        return sorted(keys)

    def serialize_user(self, user: AccessUser) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "is_superadmin": user.is_superadmin,
            "direct_permissions": sorted(item.key for item in user.direct_permissions),
            "group_ids": sorted(item.id for item in user.groups),
            "effective_permissions": self.get_effective_permissions(user),
        }

    def serialize_group(self, group: AccessGroup) -> dict:
        return {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "is_active": group.is_active,
            "permission_keys": sorted(item.key for item in group.permissions),
            "member_count": len(group.members),
        }

    def serialize_permission(self, permission: AccessPermission) -> dict:
        return {
            "id": permission.id,
            "key": permission.key,
            "label": permission.label,
            "description": permission.description,
        }

    def _resolve_permissions(self, permission_keys: list[str]) -> list[AccessPermission]:
        unique_keys = list(dict.fromkeys(permission_keys))
        if not unique_keys:
            return []
        permissions = list(self.session.scalars(select(AccessPermission).where(AccessPermission.key.in_(unique_keys))).all())
        if len(permissions) != len(unique_keys):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more permissions were not found")
        permission_by_key = {permission.key: permission for permission in permissions}
        return [permission_by_key[key] for key in unique_keys]

    def _resolve_groups(self, group_ids: list[str]) -> list[AccessGroup]:
        unique_ids = list(dict.fromkeys(group_ids))
        if not unique_ids:
            return []
        groups = list(self.session.scalars(select(AccessGroup).where(AccessGroup.id.in_(unique_ids))).all())
        if len(groups) != len(unique_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more access groups were not found")
        group_by_id = {group.id: group for group in groups}
        return [group_by_id[group_id] for group_id in unique_ids]
