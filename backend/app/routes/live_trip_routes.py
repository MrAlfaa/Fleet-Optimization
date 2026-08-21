from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.auth_middleware import require_roles
from app.services.live_trip_service import (
    get_live_trip,
    get_live_trip_events,
    get_live_trip_locations,
    list_live_trips,
)
from app.services.route_prediction_service import ROUTE_ALLOWED_ROLES
from app.utils.response import success_response


router = APIRouter(prefix="/live-trips", tags=["Live Trips"])


@router.get("")
async def live_trips(_: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES))) -> dict:
    data = await list_live_trips()
    return success_response("Live trips retrieved successfully", data=data)


@router.get("/{route_id}")
async def live_trip_detail(route_id: str, _: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES))) -> dict:
    data = await get_live_trip(route_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live trip route not found")
    return success_response("Live trip retrieved successfully", data=data)


@router.get("/{route_id}/locations")
async def live_trip_locations(
    route_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    _: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    data = await get_live_trip_locations(route_id, limit)
    return success_response("Live trip locations retrieved successfully", data=data)


@router.get("/{route_id}/events")
async def live_trip_events(
    route_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    _: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    data = await get_live_trip_events(route_id, limit)
    return success_response("Live trip events retrieved successfully", data=data)
