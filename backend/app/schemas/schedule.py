from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.schedule import ScheduleAction, ScheduleType
from app.schemas.common import AppBaseModel


class ScheduleBase(BaseModel):
    instance_id: str
    type: ScheduleType
    action: ScheduleAction
    run_at_utc: datetime | None = None
    days_of_week: list[int] | None = None
    time_utc: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    enabled: bool = True

    @model_validator(mode="after")
    def validate_schedule(self) -> "ScheduleBase":
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
    instance_id: str | None = None
    type: ScheduleType | None = None
    action: ScheduleAction | None = None
    run_at_utc: datetime | None = None
    days_of_week: list[int] | None = None
    time_utc: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    enabled: bool | None = None

    @model_validator(mode="after")
    def validate_schedule(self) -> "ScheduleUpdate":
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
    instance_id: str
    instance_name: str | None = None
    type: ScheduleType
    action: ScheduleAction
    run_at_utc: datetime | None
    days_of_week: list[int] | None
    time_utc: str | None
    enabled: bool
    last_triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime
