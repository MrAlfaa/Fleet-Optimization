from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.middleware.auth_middleware import require_roles
from app.services.report_service import build_pdf_report, build_xlsx_report


router = APIRouter(prefix="/reports", tags=["Reports"])
REPORT_ROLES = ["admin", "fleet_manager", "maintenance_manager", "route_planner"]


@router.get("/export")
async def export_report(
    format: str = Query(pattern="^(pdf|xlsx)$"),
    start_date: date | None = None,
    end_date: date | None = None,
    _: dict = Depends(require_roles(REPORT_ROLES)),
):
    if start_date and end_date and start_date > end_date:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="start_date must not be after end_date")
    start_value = datetime.combine(start_date, time.min, timezone.utc) if start_date else None
    end_value = datetime.combine(end_date, time.max, timezone.utc) if end_date else None
    if format == "pdf":
        payload, media_type, filename = await build_pdf_report(start_value, end_value), "application/pdf", "fleetopt_operational_report.pdf"
    else:
        payload, media_type, filename = await build_xlsx_report(start_value, end_value), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "fleetopt_operational_report.xlsx"
    return StreamingResponse(iter([payload]), media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})
