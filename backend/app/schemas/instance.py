from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import AppBaseModel


class InstanceBase(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    ocid: str = Field(min_length=20, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    enabled: bool = True

    @field_validator("ocid")
    @classmethod
    def validate_ocid(cls, value: str) -> str:
        if not value.startswith("ocid1.instance."):
            raise ValueError("OCID must start with ocid1.instance.")
        return value


class InstanceCreate(InstanceBase):
    pass


class InstanceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None


class InstanceRead(AppBaseModel):
    id: str
    name: str
    ocid: str
    description: str | None
    enabled: bool
    last_known_state: str | None
    created_at: datetime
    updated_at: datetime


class InstanceActionResult(BaseModel):
    status: str
    state: str | None
    stdout: str | None
    stderr: str | None

