from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ScheduleType(str, Enum):
    one_time = "one_time"
    recurring = "recurring"


class ScheduleAction(str, Enum):
    start = "start"
    stop = "stop"
    restart = "restart"


class Schedule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "schedules"

    instance_id: Mapped[str] = mapped_column(ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[ScheduleType] = mapped_column(SqlEnum(ScheduleType), nullable=False)
    action: Mapped[ScheduleAction] = mapped_column(SqlEnum(ScheduleAction), nullable=False)
    run_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    days_of_week: Mapped[list[int] | None] = mapped_column(JSON)
    time_utc: Mapped[str | None] = mapped_column(String(5))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    instance = relationship("Instance", back_populates="schedules")
