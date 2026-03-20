from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database: str
    oci_cli: str
    oci_config: str
    details: dict[str, str | None]
