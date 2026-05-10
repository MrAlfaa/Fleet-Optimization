from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.auth_middleware import require_roles
from app.models.alert_model import ALERT_SEVERITIES, ALERT_STATUSES, ALERT_TYPES
from app.schemas.alert_schema import AlertCreate
from app.services.alert_service import (
    create_alert,
    dismiss_alert,
    get_alert_by_id,
    get_alert_summary,
    list_alerts,
    resolve_alert,
)
from app.utils.response import success_response
from app.utils.validators import validate_choice


router = APIRouter(prefix="/alerts", tags=["Alerts"])


ALERT_VIEW_ROLES = ["admin", "fleet_manager", "maintenance_manager", "route_planner"]


@router.get("")
async def get_alerts(
    alert_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: dict = Depends(require_roles(ALERT_VIEW_ROLES)),
) -> dict:
    if alert_type:
        validate_choice(alert_type, ALERT_TYPES, "Alert type")
    if severity:
        validate_choice(severity, ALERT_SEVERITIES, "Alert severity")
    if status:
        validate_choice(status, ALERT_STATUSES, "Alert status")
    data = await list_alerts(alert_type, severity, status, vehicle_id, page, limit)
    return success_response("Alerts retrieved successfully", data=data)


@router.post("")
async def add_alert(
    payload: AlertCreate,
    _: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager"])),
) -> dict:
    data = await create_alert(payload.model_dump())
    return success_response("Alert created successfully", data=data)


@router.get("/summary/overview")
async def alert_summary(_: dict = Depends(require_roles(ALERT_VIEW_ROLES))) -> dict:
    data = await get_alert_summary()
    return success_response("Alert summary retrieved successfully", data=data)


@router.get("/{alert_id}")
async def get_alert(alert_id: str, _: dict = Depends(require_roles(ALERT_VIEW_ROLES))) -> dict:
    data = await get_alert_by_id(alert_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return success_response("Alert retrieved successfully", data=data)


@router.patch("/{alert_id}/resolve")
async def resolve(alert_id: str, current_user: dict = Depends(require_roles(ALERT_VIEW_ROLES))) -> dict:
    data = await resolve_alert(alert_id, current_user)
    return success_response("Alert resolved successfully", data=data)


@router.patch("/{alert_id}/dismiss")
async def dismiss(alert_id: str, current_user: dict = Depends(require_roles(ALERT_VIEW_ROLES))) -> dict:
    data = await dismiss_alert(alert_id, current_user)
    return success_response("Alert dismissed successfully", data=data)
