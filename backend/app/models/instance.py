from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Instance(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "instances"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    ocid: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text())
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_known_state: Mapped[str | None] = mapped_column(String(50))

    schedules = relationship("Schedule", back_populates="instance", cascade="all, delete-orphan")
    execution_logs = relationship("ExecutionLog", back_populates="instance", cascade="all, delete-orphan")

