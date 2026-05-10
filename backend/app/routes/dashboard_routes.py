from fastapi import APIRouter, Depends, Query

from app.middleware.auth_middleware import require_roles
from app.services.dashboard_service import (
    get_fleet_dashboard_summary,
    get_maintenance_overview,
    get_recent_alerts,
    get_upcoming_maintenance,
    get_vehicle_health_distribution,
)
from app.utils.response import success_response


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


DASHBOARD_ROLES = ["admin", "fleet_manager", "maintenance_manager"]


@router.get("/fleet-summary")
async def fleet_summary(_: dict = Depends(require_roles(DASHBOARD_ROLES))) -> dict:
    data = await get_fleet_dashboard_summary()
    return success_response("Fleet dashboard summary retrieved successfully", data=data)


@router.get("/health-distribution")
async def health_distribution(_: dict = Depends(require_roles(DASHBOARD_ROLES))) -> dict:
    data = await get_vehicle_health_distribution()
    return success_response("Vehicle health distribution retrieved successfully", data=data)


@router.get("/maintenance-overview")
async def maintenance_overview(_: dict = Depends(require_roles(DASHBOARD_ROLES))) -> dict:
    data = await get_maintenance_overview()
    return success_response("Maintenance overview retrieved successfully", data=data)


@router.get("/recent-alerts")
async def recent_alerts(
    limit: int = Query(default=10, ge=1, le=50),
    _: dict = Depends(require_roles(DASHBOARD_ROLES)),
) -> dict:
    data = await get_recent_alerts(limit)
    return success_response("Recent alerts retrieved successfully", data=data)


@router.get("/upcoming-maintenance")
async def upcoming_maintenance(
    limit: int = Query(default=10, ge=1, le=50),
    _: dict = Depends(require_roles(DASHBOARD_ROLES)),
) -> dict:
    data = await get_upcoming_maintenance(limit)
    return success_response("Upcoming maintenance retrieved successfully", data=data)
