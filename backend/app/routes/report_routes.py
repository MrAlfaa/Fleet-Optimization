from datetime import date, datetime, time, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.middleware.auth_middleware import require_roles
from app.services.report_service import (
    build_pdf_report,
    build_specialized_xlsx_report,
    build_xlsx_report,
)


router = APIRouter(prefix="/reports", tags=["Reports"])
REPORT_ROLES = ["admin", "fleet_manager", "maintenance_manager", "route_planner"]


@router.get("/export")
async def export_report(
    format: str = Query(pattern="^(pdf|xlsx)$"),
    report_type: Literal[
        "vehicle_maintenance", "vehicle_details", "daily_inspection", "inspection_summary",
        "demand_forecast", "demand_capacity", "route_optimization", "route_stop_performance",
        "consolidation_details", "driver_details", "route_details",
    ] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    vehicle_id: str | None = None,
    vehicle_category: Literal["car", "van", "truck", "bus"] | None = None,
    assessment_result: Literal["low", "medium", "high", "critical"] | None = None,
    workflow_status: Literal["clear", "service_hold", "inspection", "maintenance"] | None = None,
    inspection_status: Literal[
        "pending", "assigned", "in_progress", "completed", "decision_pending",
        "maintenance_required", "returned_to_service", "cancelled",
    ] | None = None,
    zone_id: str | None = Query(default=None, max_length=80),
    demand_level: Literal["low", "medium", "high", "very_high"] | None = None,
    route_status: Literal["draft", "optimized", "approved", "dispatched", "in_progress", "completed", "cancelled"] | None = None,
    delivery_period: Literal["first_half", "second_half"] | None = None,
    consolidation_id: str | None = Query(default=None, min_length=6, max_length=40),
    consolidation_status: Literal["active", "planning", "planned", "approved", "routed", "superseded", "failed", "cancelled"] | None = None,
    driver_id: str | None = None,
    driver_account_status: Literal["active", "inactive"] | None = None,
    device_enrollment_status: Literal["pending", "enrolled", "revoked"] | None = None,
    _: dict = Depends(require_roles(REPORT_ROLES)),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must not be after end_date")
    start_value = datetime.combine(start_date, time.min, timezone.utc) if start_date else None
    end_value = datetime.combine(end_date, time.max, timezone.utc) if end_date else None
    if report_type:
        if format != "xlsx":
            raise HTTPException(status_code=422, detail="Specialized reports are available in XLSX format only")
        payload = await build_specialized_xlsx_report(
            report_type=report_type,
            start_date=start_value,
            end_date=end_value,
            vehicle_id=vehicle_id,
            vehicle_category=vehicle_category,
            assessment_result=assessment_result,
            workflow_status=workflow_status,
            inspection_status=inspection_status,
            zone_id=zone_id,
            demand_level=demand_level,
            route_status=route_status,
            delivery_period=delivery_period,
            consolidation_id=consolidation_id,
            consolidation_status=consolidation_status,
            driver_id=driver_id,
            driver_account_status=driver_account_status,
            device_enrollment_status=device_enrollment_status,
        )
        start_label = start_date.isoformat() if start_date else "all"
        end_label = end_date.isoformat() if end_date else "all"
        filename = f"fleetopt_{report_type}_{start_label}_to_{end_label}.xlsx"
        return StreamingResponse(
            iter([payload]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    if format == "pdf":
        payload, media_type, filename = await build_pdf_report(start_value, end_value), "application/pdf", "fleetopt_operational_report.pdf"
    else:
        payload, media_type, filename = await build_xlsx_report(start_value, end_value), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "fleetopt_operational_report.xlsx"
    return StreamingResponse(iter([payload]), media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})
