from fastapi import APIRouter, Depends, Query

from app.middleware.auth_middleware import require_roles
from app.schemas.intelligence_schema import AssignmentValidationRequest
from app.services.fleet_intelligence_service import (
    get_fleet_readiness,
    get_fleet_recommendations,
    validate_vehicle_assignment,
)
from app.utils.response import success_response


router = APIRouter(prefix="/intelligence", tags=["Fleet Intelligence"])
READINESS_ROLES = ["admin", "fleet_manager", "route_planner", "maintenance_manager"]
ASSIGNMENT_ROLES = ["admin", "fleet_manager", "route_planner"]


@router.get("/fleet-readiness")
async def fleet_readiness(
    forecast_date: str | None = None,
    current_user: dict = Depends(require_roles(READINESS_ROLES)),
):
    data = await get_fleet_readiness(forecast_date)
    return success_response("Fleet readiness calculated successfully", data=data)


@router.get("/recommendations")
async def recommendations(
    days: int = Query(default=7, ge=1, le=30),
    current_user: dict = Depends(require_roles(READINESS_ROLES)),
):
    data = await get_fleet_recommendations(days)
    return success_response("Fleet intelligence recommendations retrieved successfully", data=data)


@router.post("/validate-assignment")
async def validate_assignment(
    payload: AssignmentValidationRequest,
    current_user: dict = Depends(require_roles(ASSIGNMENT_ROLES)),
):
    data = await validate_vehicle_assignment(payload.vehicle_id, payload.route_id)
    return success_response("Vehicle assignment evaluated successfully", data=data)
