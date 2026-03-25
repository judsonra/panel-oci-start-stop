from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportDailyCostRead(BaseModel):
    date: str
    amount: float


class ReportResourceCostRead(BaseModel):
    service: str | None = None
    sku_name: str | None = None
    resource_id: str | None = None
    resource_name: str | None = None
    total_amount: float


class ReportCompartmentCostRead(BaseModel):
    compartment_id: str | None = None
    compartment_name: str | None = None
    total_amount: float
    daily_costs: list[ReportDailyCostRead]
    resources: list[ReportResourceCostRead]


class CostByCompartmentReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    year: int
    month: int
    currency: str | None = None
    source: str
    sync_status: str
    available: bool
    last_refreshed_at: datetime | None = None
    total_amount: float
    daily_totals: list[ReportDailyCostRead]
    compartments: list[ReportCompartmentCostRead]


class RefreshCostReportRequest(BaseModel):
    year: int
    month: int
