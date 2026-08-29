from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.auth_middleware import get_current_user, require_roles
from app.models.route_model import ROUTE_STATUSES
from app.schemas.route_schema import (
    BatchRouteSegmentPredictionRequest,
    RouteDispatchRequest,
    RouteOptimizationRequest,
    RouteSegmentPredictionRequest,
)
from app.services.route_artifact_loader_service import RouteArtifactUnavailableError
from app.services.route_geometry_service import ensure_route_geometry_access, route_geometry_service, route_plan_coordinates
from app.services.route_optimizer_service import (
    cancel_route,
    dispatch_route,
    get_route_dashboard_summary,
    get_route_plan,
    list_route_plans,
    optimize_route,
)
from app.services.route_prediction_service import (
    ROUTE_ALLOWED_ROLES,
    ROUTE_DRIVER_VIEW_ROLES,
    get_model_metrics,
    get_model_status,
    predict_route_segment,
    predict_route_segments_batch,
)
from app.utils.response import error_response, success_response
from app.utils.validators import validate_choice


router = APIRouter(prefix="/routes", tags=["Route Optimization"])


async def require_route_geometry_user(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in ROUTE_DRIVER_VIEW_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions")
    if user.get("role") not in {"admin", "driver"} and "routes.view" not in user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission required: routes.view")
    return user


@router.get("/model/status")
async def model_status(_: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES))) -> dict:
    return success_response("Route prediction model status retrieved", data=get_model_status())


@router.get("/model/metrics")
async def model_metrics(_: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES))) -> dict:
    return success_response("Route prediction model metrics retrieved", data=get_model_metrics())


@router.post("/predict-segment")
async def predict_segment(
    payload: RouteSegmentPredictionRequest,
    _: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    try:
        data = predict_route_segment(payload.model_dump())
        return success_response("Route segment prediction completed", data=data)
    except RouteArtifactUnavailableError as exc:
        return error_response(exc.message, data=exc.data, status_code=503)


@router.post("/predict-batch")
async def predict_batch(
    payload: BatchRouteSegmentPredictionRequest,
    _: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    try:
        data = predict_route_segments_batch([segment.model_dump() for segment in payload.segments])
        return success_response("Route segment batch prediction completed", data=data)
    except RouteArtifactUnavailableError as exc:
        return error_response(exc.message, data=exc.data, status_code=503)


@router.post("/optimize")
async def optimize(
    payload: RouteOptimizationRequest,
    current_user: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    data = await optimize_route(payload.model_dump(), current_user)
    message = "Route optimized successfully"
    if not data.get("used_ml_cost"):
        message = "Route optimized using fallback distance-based cost because ML model is unavailable"
    return success_response(message, data=data)


@router.get("/dashboard-summary")
async def dashboard_summary(_: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES))) -> dict:
    data = await get_route_dashboard_summary()
    return success_response("Route dashboard summary retrieved successfully", data=data)


@router.get("")
async def get_routes(
    status: str | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    driver_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    if status:
        validate_choice(status, ROUTE_STATUSES, "Route status")
    data = await list_route_plans(status_filter=status, vehicle_id=vehicle_id, driver_id=driver_id, page=page, limit=limit)
    return success_response("Route plans retrieved successfully", data=data)


@router.get("/{route_id}")
async def get_route_detail(
    route_id: str,
    _: dict = Depends(require_roles(ROUTE_DRIVER_VIEW_ROLES)),
) -> dict:
    data = await get_route_plan(route_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    return success_response("Route plan retrieved successfully", data=data)


@router.get("/{route_id}/geometry")
async def get_route_geometry(
    route_id: str,
    current_user: dict = Depends(require_route_geometry_user),
) -> dict:
    route = await get_route_plan(route_id)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    try:
        ensure_route_geometry_access(route, current_user)
        data = await route_geometry_service.geometry(route_plan_coordinates(route))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    data["route_id"] = route_id
    return success_response("Route geometry retrieved successfully", data=data)


@router.post("/{route_id}/dispatch")
async def dispatch(
    route_id: str,
    payload: RouteDispatchRequest,
    current_user: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    data = await dispatch_route(route_id, payload.model_dump(exclude_unset=True), current_user)
    return success_response("Route dispatched successfully", data=data)


@router.post("/{route_id}/cancel")
async def cancel(
    route_id: str,
    current_user: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    data = await cancel_route(route_id, current_user)
    return success_response("Route cancelled successfully", data=data)
