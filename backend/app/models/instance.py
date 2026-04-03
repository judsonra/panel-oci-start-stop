from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Instance(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "instances"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    ocid: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text())
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_known_state: Mapped[str | None] = mapped_column(String(50))
    vcpu: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_gbs: Mapped[float | None] = mapped_column(Float, nullable=True)
    vnic_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    public_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    private_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    oci_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    schedules = relationship("Schedule", back_populates="instance", cascade="all, delete-orphan")
    execution_logs = relationship("ExecutionLog", back_populates="instance", cascade="all, delete-orphan")
