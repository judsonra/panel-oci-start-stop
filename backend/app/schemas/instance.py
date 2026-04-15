from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import AppBaseModel


class InstanceBase(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    ocid: str = Field(min_length=20, max_length=255)
    compartment_id: str | None = None
    description: str | None = Field(default=None, max_length=500)
    enabled: bool = True
    app_url: str | None = Field(default=None, max_length=255)
    environment: str | None = Field(default=None, max_length=10)
    customer_name: str | None = Field(default=None, max_length=120)
    domain: str | None = Field(default=None, max_length=120)
    name_prefix: str | None = Field(default=None, max_length=30)

    @field_validator("ocid")
    @classmethod
    def validate_ocid(cls, value: str) -> str:
        if not value.startswith("ocid1.instance."):
            raise ValueError("OCID must start with ocid1.instance.")
        return value

    @field_validator("app_url")
    @classmethod
    def validate_app_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower().rstrip(".")
        if not normalized:
            return None
        if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,63}", normalized):
            raise ValueError("app_url must be a valid hostname")
        return normalized

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized:
            return None
        if normalized not in {"HMG", "PRD"}:
            raise ValueError("environment must be HMG or PRD")
        return normalized


class InstanceCreate(InstanceBase):
    pass


class InstanceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    compartment_id: str | None = None
    description: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None
    app_url: str | None = Field(default=None, max_length=255)
    environment: str | None = Field(default=None, max_length=10)
    customer_name: str | None = Field(default=None, max_length=120)
    domain: str | None = Field(default=None, max_length=120)
    name_prefix: str | None = Field(default=None, max_length=30)

    @field_validator("app_url")
    @classmethod
    def validate_app_url(cls, value: str | None) -> str | None:
        return InstanceBase.validate_app_url(value)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str | None) -> str | None:
        return InstanceBase.validate_environment(value)


class InstanceImportCreate(BaseModel):
    ocid: str = Field(min_length=20, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    enabled: bool = True
    app_url: str | None = Field(default=None, max_length=255)

    @field_validator("ocid")
    @classmethod
    def validate_ocid(cls, value: str) -> str:
        if not value.startswith("ocid1.instance."):
            raise ValueError("OCID must start with ocid1.instance.")
        return value

    @field_validator("app_url")
    @classmethod
    def validate_app_url(cls, value: str | None) -> str | None:
        return InstanceBase.validate_app_url(value)


class InstanceRead(AppBaseModel):
    id: str
    name: str
    ocid: str
    app_url: str | None
    environment: str | None
    customer_name: str | None
    domain: str | None
    name_prefix: str | None
    compartment_id: str | None
    description: str | None
    enabled: bool
    last_known_state: str | None
    vcpu: float | None
    memory_gbs: float | None
    vnic_id: str | None
    public_ip: str | None
    private_ip: str | None
    oci_created_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InstanceActionResult(BaseModel):
    status: str
    state: str | None
    stdout: str | None
    stderr: str | None


class InstanceVnicRead(BaseModel):
    instance_ocid: str
    vnic_id: str | None


class VnicDetailsRead(BaseModel):
    vnic_id: str
    public_ip: str | None
    private_ip: str | None


class InstanceImportPreviewRead(BaseModel):
    name: str
    ocid: str
    app_url: str | None
    environment: str | None
    customer_name: str | None
    domain: str | None
    name_prefix: str | None
    vcpu: float | None
    memory_gbs: float | None
    vnic_id: str | None
    public_ip: str | None
    private_ip: str | None
    compartment_ocid: str
    compartment_name: str
    oci_created_at: datetime | None
    already_registered: bool


class InstanceImportItemRead(BaseModel):
    ocid: str
    name: str
    status: str
    message: str | None = None
    vcpu: float | None = None
    memory_gbs: float | None = None
    vnic_id: str | None = None
    public_ip: str | None = None
    private_ip: str | None = None
    oci_created_at: datetime | None = None


class CompartmentInstanceImportRead(BaseModel):
    compartment_ocid: str
    compartment_name: str
    total_instances: int
    created: int
    updated: int
    unchanged: int
    failed: int
    instances: list[InstanceImportItemRead]


class CompartmentInstancesImportRead(BaseModel):
    total_compartments: int
    processed_compartments: int
    total_instances: int
    created: int
    updated: int
    unchanged: int
    failed: int
    compartments: list[CompartmentInstanceImportRead]


class ImportInstancesJobCreateRead(BaseModel):
    job_id: str
    status: str
    started_at: datetime


class ImportInstancesJobStatusRead(BaseModel):
    job_id: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    total_compartments: int = 0
    processed_compartments: int = 0
    total_instances: int = 0
    processed_instances: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0
    current_compartment_name: str | None = None
    current_instance_name: str | None = None
    result: CompartmentInstancesImportRead | None = None
    error: str | None = None


class InstanceStatusRefreshCompartmentRead(BaseModel):
    compartment_ocid: str
    compartment_name: str
    total_oci_instances: int
    matched_instances: int
    updated: int
    unchanged: int
    failed: int
    message: str | None = None


class InstanceStatusRefreshRead(BaseModel):
    total_compartments: int
    processed_compartments: int
    matched_instances: int
    updated: int
    unchanged: int
    failed: int
    compartments: list[InstanceStatusRefreshCompartmentRead]


class ProxyResolveRead(BaseModel):
    decision: Literal["pass", "wait", "not_found", "error"]
    instance_id: str | None = None
    ocid: str | None = None
    state: str | None = None
    message: str | None = None
    retry_after_seconds: int | None = None


class AppUrlBackfillItemRead(BaseModel):
    instance_id: str
    ocid: str
    name: str
    derived_app_url: str | None
    outcome: Literal["updated", "skipped_existing", "unresolved", "failed"]
    message: str | None = None


class AppUrlBackfillResultRead(BaseModel):
    total: int
    processed: int
    updated: int
    skipped_existing: int
    unresolved: int
    failed: int
    items: list[AppUrlBackfillItemRead]


class AppUrlBackfillJobCreateRead(BaseModel):
    job_id: str
    status: str
    started_at: datetime


class AppUrlBackfillJobStatusRead(BaseModel):
    job_id: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    total: int = 0
    processed: int = 0
    updated: int = 0
    skipped_existing: int = 0
    unresolved: int = 0
    failed: int = 0
    current_instance_name: str | None = None
    result: AppUrlBackfillResultRead | None = None
    error: str | None = None
