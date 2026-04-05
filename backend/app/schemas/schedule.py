from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.schedule import ScheduleAction, ScheduleTargetType, ScheduleType
from app.schemas.common import AppBaseModel


class ScheduleBase(BaseModel):
    target_type: ScheduleTargetType
    instance_id: str | None = None
    group_id: str | None = None
    type: ScheduleType
    action: ScheduleAction
    run_at_utc: datetime | None = None
    days_of_week: list[int] | None = None
    time_utc: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    enabled: bool = True

    @model_validator(mode="after")
    def validate_schedule(self) -> "ScheduleBase":
        if self.target_type == ScheduleTargetType.instance:
            if not self.instance_id:
                raise ValueError("instance_id is required for instance schedules")
            if self.group_id is not None:
                raise ValueError("group_id is not allowed for instance schedules")
        if self.target_type == ScheduleTargetType.group:
            if not self.group_id:
                raise ValueError("group_id is required for group schedules")
            if self.instance_id is not None:
                raise ValueError("instance_id is not allowed for group schedules")
        if self.type == ScheduleType.one_time and not self.run_at_utc:
            raise ValueError("run_at_utc is required for one_time schedules")
        if self.type == ScheduleType.recurring:
            if not self.days_of_week:
                raise ValueError("days_of_week is required for recurring schedules")
            if self.time_utc is None:
                raise ValueError("time_utc is required for recurring schedules")
        return self


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    target_type: ScheduleTargetType | None = None
    instance_id: str | None = None
    group_id: str | None = None
    type: ScheduleType | None = None
    action: ScheduleAction | None = None
    run_at_utc: datetime | None = None
    days_of_week: list[int] | None = None
    time_utc: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    enabled: bool | None = None

    @model_validator(mode="after")
    def validate_schedule(self) -> "ScheduleUpdate":
        if self.target_type == ScheduleTargetType.instance:
            if not self.instance_id:
                raise ValueError("instance_id is required for instance schedules")
            if self.group_id is not None:
                raise ValueError("group_id is not allowed for instance schedules")
        if self.target_type == ScheduleTargetType.group:
            if not self.group_id:
                raise ValueError("group_id is required for group schedules")
            if self.instance_id is not None:
                raise ValueError("instance_id is not allowed for group schedules")
        if self.type == ScheduleType.one_time and self.run_at_utc is None:
            raise ValueError("run_at_utc is required for one_time schedules")
        if self.type == ScheduleType.recurring:
            if not self.days_of_week:
                raise ValueError("days_of_week is required for recurring schedules")
            if self.time_utc is None:
                raise ValueError("time_utc is required for recurring schedules")
        return self


class ScheduleRead(AppBaseModel):
    id: str
    target_type: ScheduleTargetType
    instance_id: str | None
    instance_name: str | None = None
    group_id: str | None = None
    group_name: str | None = None
    type: ScheduleType
    action: ScheduleAction
    run_at_utc: datetime | None
    days_of_week: list[int] | None
    time_utc: str | None
    enabled: bool
    last_triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime
