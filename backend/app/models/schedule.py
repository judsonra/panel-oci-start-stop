from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ScheduleType(str, Enum):
    one_time = "one_time"
    weekly = "weekly"
    monthly = "monthly"


class ScheduleTargetType(str, Enum):
    instance = "instance"
    group = "group"


class ScheduleAction(str, Enum):
    start = "start"
    stop = "stop"
    restart = "restart"


class Schedule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "schedules"

    target_type: Mapped[ScheduleTargetType] = mapped_column(SqlEnum(ScheduleTargetType), nullable=False, default=ScheduleTargetType.instance)
    instance_id: Mapped[str | None] = mapped_column(ForeignKey("instances.id", ondelete="CASCADE"), nullable=True, index=True)
    group_id: Mapped[str | None] = mapped_column(ForeignKey("groups.id", ondelete="RESTRICT"), nullable=True, index=True)
    type: Mapped[ScheduleType] = mapped_column(SqlEnum(ScheduleType), nullable=False)
    action: Mapped[ScheduleAction] = mapped_column(SqlEnum(ScheduleAction), nullable=False)
    run_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    days_of_week: Mapped[list[int] | None] = mapped_column(JSON)
    days_of_month: Mapped[list[int] | None] = mapped_column(JSON)
    time_utc: Mapped[str | None] = mapped_column(String(5))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    instance = relationship("Instance", back_populates="schedules")
    group = relationship("Group", back_populates="schedules")
