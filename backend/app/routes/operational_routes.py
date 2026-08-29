from datetime import date

from fastapi import APIRouter, Depends, Query

from app.middleware.auth_middleware import require_roles
from app.services.operational_context_service import get_operational_context, get_weather_context
from app.services.search_service import global_search
from app.services.route_optimizer_service import get_route_plan
from app.utils.response import success_response
from app.utils.branch_operations import get_branch_profile


router = APIRouter(tags=["Operational Context"])
WEB_ROLES = ["admin", "fleet_manager", "maintenance_manager", "route_planner"]


@router.get("/operations/branch")
async def operations_branch(
    _: dict = Depends(require_roles([*WEB_ROLES, "driver"])),
):
    return success_response("Operational branch retrieved", data=get_branch_profile())


@router.get("/operations/context")
async def operations_context(
    date_value: date | None = Query(default=None, alias="date"),
    _: dict = Depends(require_roles(WEB_ROLES)),
):
    return success_response("Operational context retrieved", data=await get_operational_context(date_value))


@router.get("/weather/context")
async def weather_context(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    _: dict = Depends(require_roles(WEB_ROLES)),
):
    return success_response("Weather context retrieved", data=await get_weather_context(latitude, longitude))


@router.get("/weather/route-context")
async def route_weather_context(
    route_id: str,
    _: dict = Depends(require_roles(WEB_ROLES)),
):
    route = await get_route_plan(route_id)
    if route is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Route not found")
    return success_response("Route weather context retrieved", data=route.get("weather_context") or {"available": False, "source": "open_meteo", "warnings": []})


@router.get("/search")
async def search(
    q: str = Query(min_length=2, max_length=80),
    types: str | None = None,
    current_user: dict = Depends(require_roles(WEB_ROLES)),
):
    selected = {item.strip() for item in types.split(",") if item.strip()} if types else None
    return success_response("Search results retrieved", data=await global_search(q, current_user, selected))
