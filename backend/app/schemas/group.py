from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import AppBaseModel


class GroupInstanceRead(BaseModel):
    id: str
    name: str
    ocid: str
    compartment_id: str | None


class GroupBase(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    instance_ids: list[str] = Field(min_length=1)


class GroupCreate(GroupBase):
    pass


class GroupUpdate(GroupBase):
    pass


class GroupRead(AppBaseModel):
    id: str
    name: str
    instance_count: int
    instances: list[GroupInstanceRead]
    created_at: datetime
    updated_at: datetime


class GroupTreeInstanceRead(BaseModel):
    id: str
    name: str
    ocid: str


class GroupTreeCompartmentRead(BaseModel):
    id: str
    name: str
    instances: list[GroupTreeInstanceRead]
