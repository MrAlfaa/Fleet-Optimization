from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.middleware.auth_middleware import require_roles
from app.schemas.demand_schema import DemandForecastRefreshRequest
from app.services.demand_artifact_loader_service import DemandArtifactUnavailableError
from app.services.demand_forecasting_service import (
    DEMAND_ALLOWED_ROLES,
    export_forecasts_as_csv,
    get_demand_dashboard_summary,
    get_fleet_planning_recommendations,
    get_latest_forecast_summary,
    get_model_metrics,
    get_model_status,
    get_zone_adjacency_graph,
    get_zone_forecast,
    import_artifact_forecasts_to_database,
    list_forecasts,
    list_zones,
    refresh_forecast_from_model,
)
from app.utils.response import error_response, success_response


router = APIRouter(prefix="/demand", tags=["Demand Forecasting"])


@router.get("/model/status")
async def model_status(current_user: dict = Depends(require_roles(DEMAND_ALLOWED_ROLES))):
    status = await get_model_status(load_model=True)
    return success_response("Demand forecasting model status retrieved", data=status)


@router.get("/model/metrics")
async def model_metrics(current_user: dict = Depends(require_roles(DEMAND_ALLOWED_ROLES))):
    metrics = await get_model_metrics()
    return success_response("Demand forecasting model metrics retrieved", data=metrics)


@router.post("/import-artifacts")
async def import_artifacts(current_user: dict = Depends(require_roles(DEMAND_ALLOWED_ROLES))):
    try:
        result = await import_artifact_forecasts_to_database(current_user=current_user)
        return success_response("Demand forecasts imported successfully", data=result)
    except DemandArtifactUnavailableError as exc:
        return error_response(exc.message, data=exc.data, status_code=503)


@router.get("/zones")
async def zones(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_roles(DEMAND_ALLOWED_ROLES)),
):
    result = await list_zones(search=search, page=page, limit=limit)
    return success_response("Demand zones retrieved successfully", data=result)


@router.get("/forecasts")
async def forecasts(
    zone_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    demand_level: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_roles(DEMAND_ALLOWED_ROLES)),
):
    result = await list_forecasts(
        zone_id=zone_id,
        start_date=start_date,
        end_date=end_date,
        demand_level=demand_level,
        page=page,
        limit=limit,
    )
    return success_response("Demand forecasts retrieved successfully", data=result)


@router.post("/refresh")
async def refresh(
    request: DemandForecastRefreshRequest,
    current_user: dict = Depends(require_roles(DEMAND_ALLOWED_ROLES)),
):
    try:
        result = await refresh_forecast_from_model(
            days=request.days or 30,
            save_to_database=request.save_to_database,
            source=request.source,
            current_user=current_user,
        )
        message = "Demand forecast refreshed successfully"
        if result.get("fallback_used"):
            message = "Demand forecast refreshed using artifact fallback"
        return success_response(message, data=result)
    except DemandArtifactUnavailableError as exc:
        return error_response(exc.message, data=exc.data, status_code=503)


@router.get("/planning-recommendations")
async def planning_recommendations(
    zone_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    demand_level: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_roles(DEMAND_ALLOWED_ROLES)),
):
    result = await get_fleet_planning_recommendations(
        zone_id=zone_id,
        start_date=start_date,
        end_date=end_date,
        demand_level=demand_level,
        page=page,
        limit=limit,
    )
    return success_response("Fleet planning recommendations retrieved successfully", data=result)


@router.get("/dashboard-summary")
async def dashboard_summary(current_user: dict = Depends(require_roles(DEMAND_ALLOWED_ROLES))):
    result = await get_demand_dashboard_summary()
    return success_response("Demand dashboard summary retrieved successfully", data=result)


@router.get("/adjacency-graph")
async def adjacency_graph(current_user: dict = Depends(require_roles(DEMAND_ALLOWED_ROLES))):
    result = await get_zone_adjacency_graph()
    return success_response("Zone adjacency graph retrieved successfully", data=result)


@router.get("/export")
async def export(current_user: dict = Depends(require_roles(DEMAND_ALLOWED_ROLES))):
    csv_text = await export_forecasts_as_csv()
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=demand_forecasts.csv"},
    )


@router.get("/summary/latest")
async def latest_summary(current_user: dict = Depends(require_roles(DEMAND_ALLOWED_ROLES))):
    result = await get_latest_forecast_summary()
    return success_response("Latest demand forecast summary retrieved successfully", data=result)


@router.get("/forecasts/{zone_id}")
async def zone_forecast(
    zone_id: str,
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(require_roles(DEMAND_ALLOWED_ROLES)),
):
    result = await get_zone_forecast(zone_id, days=days)
    return success_response("Zone demand forecast retrieved successfully", data=result)
