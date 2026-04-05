from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import AppBaseModel


class InstanceBase(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    ocid: str = Field(min_length=20, max_length=255)
    compartment_id: str | None = None
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
    compartment_id: str | None = None
    description: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None


class InstanceImportCreate(BaseModel):
    ocid: str = Field(min_length=20, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    enabled: bool = True

    @field_validator("ocid")
    @classmethod
    def validate_ocid(cls, value: str) -> str:
        if not value.startswith("ocid1.instance."):
            raise ValueError("OCID must start with ocid1.instance.")
        return value


class InstanceRead(AppBaseModel):
    id: str
    name: str
    ocid: str
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
