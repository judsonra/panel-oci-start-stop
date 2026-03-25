from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "OCI Automation Reports API"
    database_url: str = "postgresql+psycopg://oci_user:oci_password@postgres:5432/oci_automation"
    oci_cli_path: str = "oci"
    oci_cli_profile: str = "DEFAULT"
    oci_config_dir: str = "/home/appuser/.oci"
    oci_tenant_id: str = ""
    suppress_oci_label_warning: bool = True
    cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
