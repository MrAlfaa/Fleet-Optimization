from fastapi import APIRouter, Depends, Query

from app.middleware.auth_middleware import require_roles
from app.schemas.predictive_schema import BatchPredictiveMaintenanceRequest, PredictiveMaintenanceRequest
from app.services.ml_model_loader_service import ModelUnavailableError
from app.services.predictive_maintenance_service import (
    PREDICTIVE_ALLOWED_ROLES,
    get_fleet_risk_summary,
    get_manual_ev_sensor_input_template,
    get_model_status,
    get_prediction_by_id,
    get_vehicle_prediction_history,
    list_predictions,
    predict_batch_maintenance,
    predict_vehicle_maintenance,
    simulate_vehicle_prediction,
)
from app.utils.response import error_response, success_response


router = APIRouter(prefix="/predictive-maintenance", tags=["Predictive Maintenance"])


@router.get("/model/status")
async def model_status(current_user: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    status = await get_model_status(load_model=True)
    return success_response("Predictive maintenance model status retrieved", data=status)


@router.post("/predict")
async def predict(
    request: PredictiveMaintenanceRequest,
    current_user: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES)),
):
    try:
        result = await predict_vehicle_maintenance(request, current_user)
        return success_response("Predictive maintenance prediction completed", data=result)
    except ModelUnavailableError as exc:
        return error_response(exc.message, data=exc.data, status_code=503)


@router.post("/predict-batch")
async def predict_batch(
    request: BatchPredictiveMaintenanceRequest,
    current_user: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES)),
):
    try:
        result = await predict_batch_maintenance(request, current_user)
        return success_response("Batch predictive maintenance completed", data=result)
    except ModelUnavailableError as exc:
        return error_response(exc.message, data=exc.data, status_code=503)


@router.get("/predictions")
async def predictions(
    vehicle_id: str | None = None,
    risk_level: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES)),
):
    result = await list_predictions(vehicle_id=vehicle_id, risk_level=risk_level, page=page, limit=limit)
    return success_response("Predictions retrieved successfully", data=result)


@router.get("/vehicle/{vehicle_id}/history")
async def vehicle_history(
    vehicle_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES)),
):
    result = await get_vehicle_prediction_history(vehicle_id, limit)
    return success_response("Vehicle prediction history retrieved successfully", data=result)


@router.get("/fleet-risk-summary")
async def fleet_risk_summary(current_user: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    result = await get_fleet_risk_summary()
    return success_response("Fleet risk summary retrieved successfully", data=result)


@router.get("/input-template")
async def input_template(current_user: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    return success_response(
        "Manual EV sensor input template retrieved",
        data={
            "input_source": "manual",
            "sensor_data": get_manual_ev_sensor_input_template(),
            "notes": "Use this template for manual testing until IoT ingestion is implemented.",
        },
    )


@router.post("/simulate/{vehicle_id}")
async def simulate(
    vehicle_id: str,
    current_user: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES)),
):
    try:
        result = await simulate_vehicle_prediction(vehicle_id, current_user)
        return success_response("Simulated predictive maintenance prediction completed", data=result)
    except ModelUnavailableError as exc:
        return error_response(exc.message, data=exc.data, status_code=503)


@router.get("/predictions/{prediction_id}")
async def prediction_detail(
    prediction_id: str,
    current_user: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES)),
):
    result = await get_prediction_by_id(prediction_id)
    return success_response("Prediction retrieved successfully", data=result)
