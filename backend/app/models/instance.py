from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


group_instances = Table(
    "group_instances",
    Base.metadata,
    Column("group_id", String(), ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    Column("instance_id", String(), ForeignKey("instances.id", ondelete="CASCADE"), primary_key=True),
)


class Instance(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "instances"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    ocid: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    compartment_id: Mapped[str | None] = mapped_column(ForeignKey("compartments.id", ondelete="SET NULL"), index=True)
    description: Mapped[str | None] = mapped_column(Text())
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_known_state: Mapped[str | None] = mapped_column(String(50))
    vcpu: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_gbs: Mapped[float | None] = mapped_column(Float, nullable=True)
    vnic_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    public_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    private_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    oci_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    compartment = relationship("Compartment", back_populates="instances")
    schedules = relationship("Schedule", back_populates="instance", cascade="all, delete-orphan")
    execution_logs = relationship("ExecutionLog", back_populates="instance", cascade="all, delete-orphan")
    groups = relationship("Group", secondary=group_instances, back_populates="instances")
