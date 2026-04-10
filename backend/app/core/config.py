from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "OCI Automation API"
    database_url: str = "postgresql+psycopg://oci_user:oci_password@postgres:5432/oci_automation"
    oci_cli_path: str = "oci"
    oci_cli_profile: str = "DEFAULT"
    oci_config_dir: str = "/home/appuser/.oci"
    oci_tenant_id: str = ""
    auth_enabled: bool = False
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    allowed_groups: str = ""
    entra_auth_enabled: bool = False
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_authority: str = ""
    entra_redirect_uri: str = ""
    entra_post_logout_redirect_uri: str = ""
    entra_scopes: str = "openid profile email"
    entra_jwks_url: str = ""
    entra_issuer: str = ""
    entra_audience: str = ""
    local_admin_enabled: bool = False
    local_admin_email: str = ""
    local_admin_password_hash: str = ""
    local_auth_jwt_secret: str = ""
    local_auth_jwt_expires_minutes: int = 480
    app_timezone: str = "UTC"
    scheduler_poll_seconds: int = 30
    scheduler_enabled: bool = True
    schedule_group_max_concurrency: int = 10
    cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200"
    deskmanager_auth_url: str = ""
    deskmanager_tickets_url: str = ""
    deskmanager_approver_token: str = ""
    deskmanager_public_key: str = ""
    deskmanager_solicitacao_id: str = ""
    deskmanager_impacto_id: str = ""
    deskmanager_urgencia_id: str = ""
    deskmanager_categoria_id: str = ""
    deskmanager_categoria_tipo_id: str = ""
    deskmanager_grupo_id: str = ""

    @property
    def allowed_groups_list(self) -> list[str]:
        return [group.strip() for group in self.allowed_groups.split(",") if group.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def entra_scopes_list(self) -> list[str]:
        return [scope.strip() for scope in self.entra_scopes.split(" ") if scope.strip()]

    @property
    def entra_token_url(self) -> str:
        authority = self.entra_authority.strip().rstrip("/")
        return f"{authority}/oauth2/v2.0/token" if authority else ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
