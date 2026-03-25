from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ReportPeriod(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "report_periods"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_report_period_year_month"),)

    year: Mapped[int] = mapped_column(nullable=False)
    month: Mapped[int] = mapped_column(nullable=False)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="oci")
    sync_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal("0"))

    entries: Mapped[list["ReportCostEntry"]] = relationship(
        back_populates="period", cascade="all, delete-orphan", passive_deletes=True
    )


class ReportCostEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "report_cost_entries"

    period_id: Mapped[str] = mapped_column(ForeignKey("report_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    compartment_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    compartment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sku_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    period: Mapped[ReportPeriod] = relationship(back_populates="entries")
