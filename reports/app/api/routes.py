from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.report import CostByCompartmentReportRead, RefreshCostReportRequest
from app.services.report_service import ReportService


router = APIRouter()
report_service = ReportService()


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/reports/cost-by-compartment", response_model=CostByCompartmentReportRead)
def get_cost_by_compartment(year: int, month: int, db: Session = Depends(get_db_session)) -> CostByCompartmentReportRead:
    return report_service.get_cached_cost_by_compartment(db, year, month)


@router.get("/api/reports/cost-by-compartment.csv")
def export_cost_by_compartment_csv(year: int, month: int, db: Session = Depends(get_db_session)) -> Response:
    csv_payload = report_service.export_cost_by_compartment_csv(db, year, month)
    filename = f"cost-by-compartment-{year:04d}-{month:02d}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=csv_payload, media_type="text/csv", headers=headers)


@router.post("/api/reports/cost-by-compartment/refresh", response_model=CostByCompartmentReportRead)
def refresh_cost_by_compartment(
    payload: RefreshCostReportRequest, db: Session = Depends(get_db_session)
) -> CostByCompartmentReportRead:
    try:
        return report_service.refresh_cost_by_compartment(db, payload.year, payload.month)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
