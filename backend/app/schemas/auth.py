from __future__ import annotations

from pydantic import BaseModel, Field


class AuthConfigRead(BaseModel):
    entra_enabled: bool
    local_enabled: bool
    authority: str | None = None
    client_id: str | None = None
    redirect_uri: str | None = None
    post_logout_redirect_uri: str | None = None
    scopes: list[str] = Field(default_factory=list)


class LocalLoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class EntraExchangeRequest(BaseModel):
    code: str
    code_verifier: str
    redirect_uri: str


class AuthTokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUserRead(BaseModel):
    subject: str
    email: str | None
    groups: list[str]
    permissions: list[str]
    auth_source: str
    is_superadmin: bool
    access_user_id: str | None = None
