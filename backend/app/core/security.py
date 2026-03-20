from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    subject: str
    email: str | None
    groups: list[str]


class TokenVerifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jwks: dict[str, Any] | None = None

    async def _get_jwks(self) -> dict[str, Any]:
        if self._jwks is not None:
            return self._jwks
        if not self.settings.oidc_jwks_url:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OIDC JWKS URL not configured")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self.settings.oidc_jwks_url)
            response.raise_for_status()
            self._jwks = response.json()
            return self._jwks

    async def verify(self, token: str) -> CurrentUser:
        jwks = await self._get_jwks()
        header = jwt.get_unverified_header(token)
        key = next((item for item in jwks.get("keys", []) if item.get("kid") == header.get("kid")), None)
        if key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown token signing key")
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
        claims = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            audience=self.settings.oidc_audience or None,
            issuer=self.settings.oidc_issuer or None,
        )
        groups = claims.get("groups", [])
        allowed_groups = self.settings.allowed_groups_list
        if allowed_groups and not any(group in allowed_groups for group in groups):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not allowed")
        return CurrentUser(subject=claims.get("sub", ""), email=claims.get("preferred_username"), groups=groups)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if not settings.auth_enabled:
        return CurrentUser(subject="local-dev", email="local@example.com", groups=["local"])
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    verifier = TokenVerifier(settings)
    return await verifier.verify(credentials.credentials)
