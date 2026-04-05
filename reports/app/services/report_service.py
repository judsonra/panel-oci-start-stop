import csv
import io
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.report import ReportCostEntry, ReportPeriod
from app.schemas.report import (
    CostByCompartmentReportRead,
    ReportCompartmentCostRead,
    ReportDailyCostRead,
    ReportDetailedCostRead,
    ReportResourceCostRead,
)
from app.services.oci_usage import OCIUsageService


class ReportService:
    def __init__(self, usage_service: OCIUsageService | None = None) -> None:
        self.usage_service = usage_service or OCIUsageService()

    def get_cached_cost_by_compartment(self, db: Session, year: int, month: int) -> CostByCompartmentReportRead:
        period = self._load_period(db, year, month)
        if period is None:
            return CostByCompartmentReportRead(
                year=year,
                month=month,
                currency=None,
                source="cache",
                sync_status="missing",
                available=False,
                last_refreshed_at=None,
                total_amount=0.0,
                daily_totals=[],
                compartments=[],
                detailed_items=[],
            )
        return self._build_report_response(period, source="cache")

    def refresh_cost_by_compartment(self, db: Session, year: int, month: int) -> CostByCompartmentReportRead:
        dataset = self.usage_service.fetch_cost_by_compartment(year, month)
        period = self._load_period(db, year, month)
        if period is None:
            period = ReportPeriod(year=year, month=month)
            db.add(period)
            db.flush()
        period.currency = dataset.currency
        period.source = "oci"
        period.sync_status = "ready"
        period.last_refreshed_at = datetime.now(UTC)
        period.total_amount = dataset.total_amount
        period.entries.clear()
        for entry in dataset.entries:
            period.entries.append(
                ReportCostEntry(
                    usage_date=entry.usage_date,
                    compartment_id=entry.compartment_id,
                    compartment_name=entry.compartment_name,
                    service=entry.service,
                    sku_name=entry.sku_name,
                    resource_id=entry.resource_id,
                    resource_name=entry.resource_name,
                    currency=entry.currency,
                    amount=entry.amount,
                )
            )
        db.commit()
        period = self._load_period(db, year, month)
        if period is None:
            raise RuntimeError("Failed to load refreshed cost report from database")
        return self._build_report_response(period, source="oci")

    def export_cost_by_compartment_csv(self, db: Session, year: int, month: int) -> str:
        period = self._load_period(db, year, month)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["date", "compartment_id", "compartment_name", "service", "sku_name", "resource_id", "resource_name", "amount", "currency"])
        if period is not None:
            for entry in sorted(period.entries, key=lambda item: (item.usage_date, item.compartment_name or "", item.service or "")):
                writer.writerow(
                    [
                        entry.usage_date.isoformat(),
                        entry.compartment_id or "",
                        entry.compartment_name or "",
                        entry.service or "",
                        entry.sku_name or "",
                        entry.resource_id or "",
                        entry.resource_name or "",
                        f"{float(entry.amount):.6f}",
                        entry.currency or period.currency or "",
                    ]
                )
        return output.getvalue()

    def _load_period(self, db: Session, year: int, month: int) -> ReportPeriod | None:
        statement = (
            select(ReportPeriod)
            .where(ReportPeriod.year == year, ReportPeriod.month == month)
            .options(selectinload(ReportPeriod.entries))
        )
        return db.execute(statement).scalar_one_or_none()

    def _build_report_response(self, period: ReportPeriod, source: str) -> CostByCompartmentReportRead:
        daily_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        compartment_totals: dict[tuple[str | None, str | None], Decimal] = defaultdict(lambda: Decimal("0"))
        compartment_daily: dict[tuple[str | None, str | None], dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
        compartment_resources: dict[tuple[str | None, str | None], dict[tuple[str | None, str | None, str | None, str | None], Decimal]] = defaultdict(
            lambda: defaultdict(lambda: Decimal("0"))
        )

        for entry in period.entries:
            day_key = entry.usage_date.isoformat()
            compartment_key = (entry.compartment_id, entry.compartment_name)
            resource_key = (entry.service, entry.sku_name, entry.resource_id, entry.resource_name)
            daily_totals[day_key] += entry.amount
            compartment_totals[compartment_key] += entry.amount
            compartment_daily[compartment_key][day_key] += entry.amount
            compartment_resources[compartment_key][resource_key] += entry.amount

        compartments: list[ReportCompartmentCostRead] = []
        for compartment_key, amount in sorted(compartment_totals.items(), key=lambda item: item[1], reverse=True):
            resource_items = compartment_resources[compartment_key]
            compartments.append(
                ReportCompartmentCostRead(
                    compartment_id=compartment_key[0],
                    compartment_name=compartment_key[1] or "Compartimento não informado",
                    total_amount=float(amount),
                    daily_costs=[
                        ReportDailyCostRead(date=date_key, amount=float(day_amount))
                        for date_key, day_amount in sorted(compartment_daily[compartment_key].items())
                    ],
                    resources=[
                        ReportResourceCostRead(
                            service=resource_key[0],
                            sku_name=resource_key[1],
                            resource_id=resource_key[2],
                            resource_name=resource_key[3],
                            total_amount=float(resource_amount),
                        )
                        for resource_key, resource_amount in sorted(resource_items.items(), key=lambda item: item[1], reverse=True)
                    ],
                )
            )

        return CostByCompartmentReportRead(
            year=period.year,
            month=period.month,
            currency=period.currency,
            source=source,
            sync_status=period.sync_status,
            available=True,
            last_refreshed_at=period.last_refreshed_at,
            total_amount=float(period.total_amount),
            daily_totals=[ReportDailyCostRead(date=date_key, amount=float(amount)) for date_key, amount in sorted(daily_totals.items())],
            compartments=compartments,
            detailed_items=[
                ReportDetailedCostRead(
                    date=entry.usage_date.isoformat(),
                    compartment_id=entry.compartment_id,
                    compartment_name=entry.compartment_name or "Compartimento não informado",
                    service=entry.service,
                    sku_name=entry.sku_name,
                    resource_id=entry.resource_id,
                    resource_name=entry.resource_name,
                    total_amount=float(entry.amount),
                )
                for entry in sorted(
                    period.entries,
                    key=lambda item: (
                        item.usage_date,
                        item.compartment_name or "",
                        item.service or "",
                        item.sku_name or "",
                        item.resource_name or item.resource_id or "",
                    ),
                )
            ],
        )
