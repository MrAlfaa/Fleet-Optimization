from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.auth_middleware import require_roles
from app.schemas.route_schema import RouteSetDriverAssignment
from app.services.route_prediction_service import ROUTE_ALLOWED_ROLES
from app.services.route_set_service import (
    approve_route_set,
    assign_route_driver,
    create_route_set,
    dispatch_route_set,
    get_route_set,
)
from app.utils.response import success_response


router = APIRouter(prefix="/route-sets", tags=["Route Sets"])


@router.post("/from-load-plan/{plan_id}")
async def create(plan_id: str, current_user: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES))) -> dict:
    return success_response("Route set generated", data=await create_route_set(plan_id, current_user))


@router.get("/{route_set_id}")
async def detail(route_set_id: str, _: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES))) -> dict:
    item = await get_route_set(route_set_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route set not found")
    return success_response("Route set retrieved", data=item)


@router.post("/{route_set_id}/approve")
async def approve(route_set_id: str, current_user: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES))) -> dict:
    return success_response("Route set approved", data=await approve_route_set(route_set_id, current_user))


@router.post("/{route_set_id}/routes/{route_id}/assign-driver")
async def assign_driver(
    route_set_id: str,
    route_id: str,
    payload: RouteSetDriverAssignment,
    current_user: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    return success_response(
        "Driver assigned to approved route",
        data=await assign_route_driver(route_set_id, route_id, payload.driver_id, current_user),
    )


@router.post("/{route_set_id}/dispatch")
async def dispatch(route_set_id: str, current_user: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES))) -> dict:
    return success_response("Route set dispatched", data=await dispatch_route_set(route_set_id, current_user))
