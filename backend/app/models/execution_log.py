from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class ExecutionSource(str, Enum):
    manual = "manual"
    schedule = "schedule"


class ExecutionStatus(str, Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class ExecutionLog(UUIDMixin, Base):
    __tablename__ = "execution_logs"

    instance_id: Mapped[str] = mapped_column(ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[ExecutionSource] = mapped_column(SqlEnum(ExecutionSource), nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(SqlEnum(ExecutionStatus), nullable=False, default=ExecutionStatus.pending)
    stdout_summary: Mapped[str | None] = mapped_column(Text())
    stderr_summary: Mapped[str | None] = mapped_column(Text())
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    instance = relationship("Instance", back_populates="execution_logs")
