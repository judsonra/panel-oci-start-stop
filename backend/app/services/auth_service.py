from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import httpx
import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.access_control import AccessUser
from app.schemas.auth import AuthConfigRead, AuthTokenRead, CurrentUserRead
from app.services.access_control_service import AccessControlService
from app.services.audit_service import AuditService
from app.core.security import CurrentUser


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.access_control = AccessControlService(session)
        self.audit = AuditService(session)

    def get_public_config(self) -> AuthConfigRead:
        return AuthConfigRead(
            entra_enabled=self.settings.entra_auth_enabled,
            local_enabled=self.settings.local_admin_enabled,
            authority=self.settings.entra_authority or None,
            client_id=self.settings.entra_client_id or None,
            redirect_uri=self.settings.entra_redirect_uri or None,
            post_logout_redirect_uri=self.settings.entra_post_logout_redirect_uri or None,
            scopes=self.settings.entra_scopes_list,
        )

    def login_local(self, *, email: str, password: str, ip_address: str | None, user_agent: str | None) -> AuthTokenRead:
        if not self.settings.local_admin_enabled:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local admin access is disabled")
        if not self.settings.local_admin_email.strip() or not self.settings.local_admin_password_hash.strip():
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Local admin credentials are not configured")
        if email.strip().casefold() != self.settings.local_admin_email.strip().casefold():
            self.audit.log_access_event(
                event_type="login_failed",
                auth_source="local_admin",
                email=email.strip().casefold() or None,
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid local admin credentials",
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not bcrypt.checkpw(password.encode("utf-8"), self.settings.local_admin_password_hash.encode("utf-8")):
            self.audit.log_access_event(
                event_type="login_failed",
                auth_source="local_admin",
                email=email.strip().casefold(),
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid local admin credentials",
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        token = self._build_app_token(
            subject=email.strip().casefold(),
            email=email.strip().casefold(),
            auth_source="local_admin",
            access_user_id=None,
            is_superadmin=True,
        )
        self.audit.log_access_event(
            event_type="login_success",
            auth_source="local_admin",
            email=email.strip().casefold(),
            ip_address=ip_address,
            user_agent=user_agent,
            status_code=status.HTTP_200_OK,
            message="Local admin login succeeded",
        )
        return token

    async def exchange_entra_code(
        self,
        *,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuthTokenRead:
        if not self.settings.entra_auth_enabled:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entra authentication is disabled")
        required = [
            self.settings.entra_authority,
            self.settings.entra_client_id,
            self.settings.entra_redirect_uri,
            self.settings.entra_jwks_url,
            self.settings.entra_issuer,
        ]
        if any(not item.strip() for item in required):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Entra configuration is incomplete")
        token_url = self.settings.entra_token_url
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.settings.entra_client_id,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            payload = response.json()
            if response.status_code >= 400:
                self.audit.log_access_event(
                    event_type="login_failed",
                    auth_source="entra",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status_code=response.status_code,
                    message="Entra code exchange failed",
                )
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Entra authentication failed")
            id_token = payload.get("id_token")
            if not isinstance(id_token, str) or not id_token:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Entra id_token was not returned")
            claims = await self._verify_entra_token(id_token)

        email = (claims.get("preferred_username") or claims.get("email") or "").strip().casefold()
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Entra token email was not provided")
        access_user = self.access_control.get_user_by_email(email)
        if access_user is None or not access_user.is_active:
            self.audit.log_access_event(
                event_type="access_denied",
                auth_source="entra",
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=status.HTTP_403_FORBIDDEN,
                message="User is not pre-registered for Entra access",
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not allowed")
        token = self._build_app_token(
            subject=claims.get("sub", email),
            email=email,
            auth_source="entra",
            access_user_id=access_user.id,
            is_superadmin=access_user.is_superadmin,
        )
        self.audit.log_access_event(
            event_type="login_success",
            auth_source="entra",
            email=email,
            user_id=access_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            status_code=status.HTTP_200_OK,
            message="Entra login succeeded",
        )
        return token

    async def _verify_entra_token(self, token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self.settings.entra_jwks_url)
            response.raise_for_status()
            jwks = response.json()
        header = jwt.get_unverified_header(token)
        key = next((item for item in jwks.get("keys", []) if item.get("kid") == header.get("kid")), None)
        if key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown Entra signing key")
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
        return jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            audience=self.settings.entra_audience or self.settings.entra_client_id,
            issuer=self.settings.entra_issuer,
        )

    def authenticate_app_token(self, token: str) -> CurrentUser:
        if not self.settings.local_auth_jwt_secret.strip():
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Local auth signing secret is not configured")
        try:
            claims = jwt.decode(token, self.settings.local_auth_jwt_secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token") from exc
        auth_source = claims.get("auth_source") or "unknown"
        email = claims.get("email")
        if auth_source == "local_admin":
            from app.services.access_catalog import ACCESS_PERMISSION_CATALOG

            return CurrentUser(
                subject=claims.get("sub", ""),
                email=email,
                groups=["local_admin"],
                permissions=[item[0] for item in ACCESS_PERMISSION_CATALOG],
                auth_source="local_admin",
                is_superadmin=True,
                access_user_id=None,
            )
        access_user_id = claims.get("access_user_id")
        if not isinstance(access_user_id, str) or not access_user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access user token")
        access_user = self.access_control.get_user(access_user_id)
        if not access_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not active")
        permissions = self.access_control.get_effective_permissions(access_user)
        return CurrentUser(
            subject=claims.get("sub", access_user.email),
            email=access_user.email,
            groups=[group.name for group in access_user.groups if group.is_active],
            permissions=permissions,
            auth_source=auth_source,
            is_superadmin=access_user.is_superadmin,
            access_user_id=access_user.id,
        )

    def build_current_user_read(self, current_user: CurrentUser) -> CurrentUserRead:
        return CurrentUserRead(**asdict(current_user))

    def create_logout_audit(self, current_user: CurrentUser, *, ip_address: str | None, user_agent: str | None) -> None:
        self.audit.log_access_event(
            event_type="logout",
            auth_source=current_user.auth_source,
            email=current_user.email,
            user_id=current_user.access_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status_code=status.HTTP_200_OK,
            message="Logout succeeded",
        )

    def _build_app_token(
        self,
        *,
        subject: str,
        email: str | None,
        auth_source: str,
        access_user_id: str | None,
        is_superadmin: bool,
    ) -> AuthTokenRead:
        expires_in = max(1, self.settings.local_auth_jwt_expires_minutes) * 60
        issued_at = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "email": email,
            "auth_source": auth_source,
            "access_user_id": access_user_id,
            "is_superadmin": is_superadmin,
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + timedelta(seconds=expires_in)).timestamp()),
        }
        token = jwt.encode(payload, self.settings.local_auth_jwt_secret, algorithm="HS256")
        return AuthTokenRead(access_token=token, expires_in=expires_in)
