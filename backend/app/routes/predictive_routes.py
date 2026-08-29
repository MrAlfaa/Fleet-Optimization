from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.auth_middleware import require_roles
from app.schemas.predictive_schema import (
    BatchPredictiveMaintenanceRequest, PredictionReviewResolveRequest,
    PredictiveMaintenanceRequest, PredictiveRecalculateRequest,
)
from app.services.ml_model_loader_service import ModelUnavailableError
from app.services.maintenance_eligibility_service import get_assessment_eligibility
from app.services.predictive_maintenance_service import (
    PREDICTIVE_ALLOWED_ROLES, REVIEW_RESOLVER_ROLES, get_current_vehicle_prediction,
    get_fleet_risk_summary, get_model_status, get_prediction_by_id,
    get_vehicle_prediction_history, list_prediction_reviews, list_predictions,
    predict_batch_maintenance, predict_vehicle_maintenance, recalculate_vehicle_maintenance,
    resolve_prediction_review,
)
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/predictive-maintenance", tags=["Predictive Maintenance"])


async def _status_response():
    return success_response("Predictive maintenance model status retrieved", data=await get_model_status())


@router.get("/model-status")
async def model_status(_: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    return await _status_response()


@router.get("/model/status", include_in_schema=False)
async def legacy_model_status(_: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    return await _status_response()


@router.post("/vehicles/{vehicle_id}/recalculate")
async def recalculate(vehicle_id: str, payload: PredictiveRecalculateRequest,
                      current_user: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    try:
        data = await recalculate_vehicle_maintenance(vehicle_id, payload.model_dump(), current_user)
        return success_response("Vehicle maintenance risk recalculated", data=data)
    except ModelUnavailableError as exc:
        return error_response(exc.message, data=exc.data, status_code=503)


@router.get("/vehicles/{vehicle_id}/eligibility")
async def assessment_eligibility(
    vehicle_id: str,
    _: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES)),
):
    return success_response(
        "Vehicle assessment readiness retrieved",
        data=await get_assessment_eligibility(vehicle_id),
    )


@router.get("/vehicles/{vehicle_id}/current")
async def current_prediction(vehicle_id: str, _: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    data = await get_current_vehicle_prediction(vehicle_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No prediction is available for this vehicle")
    return success_response("Current vehicle prediction retrieved", data=data)


@router.get("/vehicles/{vehicle_id}/history")
async def vehicle_history(vehicle_id: str, limit: int = Query(default=20, ge=1, le=100),
                          _: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    return success_response("Vehicle prediction history retrieved", data=await get_vehicle_prediction_history(vehicle_id, limit))


@router.get("/vehicle/{vehicle_id}/history", include_in_schema=False)
async def legacy_vehicle_history(vehicle_id: str, limit: int = Query(default=20, ge=1, le=100),
                                 _: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    return success_response("Vehicle prediction history retrieved", data=await get_vehicle_prediction_history(vehicle_id, limit))


@router.get("/reviews")
async def reviews(status_filter: str | None = Query(default=None, alias="status"),
                  page: int = Query(default=1, ge=1), limit: int = Query(default=50, ge=1, le=100),
                  _: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    return success_response("Engineering reviews retrieved", data=await list_prediction_reviews(status_filter, page, limit))


@router.post("/reviews/{review_id}/resolve")
async def resolve_review(review_id: str, payload: PredictionReviewResolveRequest,
                         current_user: dict = Depends(require_roles(REVIEW_RESOLVER_ROLES))):
    data = await resolve_prediction_review(review_id, payload.model_dump(), current_user)
    return success_response("Engineering review resolved", data=data)


@router.post("/predict", include_in_schema=False)
async def predict(payload: PredictiveMaintenanceRequest,
                  current_user: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    try:
        return success_response("Vehicle maintenance risk recalculated", data=await predict_vehicle_maintenance(payload, current_user))
    except ModelUnavailableError as exc:
        return error_response(exc.message, data=exc.data, status_code=503)


@router.post("/predict-batch", include_in_schema=False)
async def predict_batch(payload: BatchPredictiveMaintenanceRequest,
                        current_user: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    return success_response("Batch maintenance risk recalculated", data=await predict_batch_maintenance(payload, current_user))


@router.get("/predictions")
async def predictions(vehicle_id: str | None = None, risk_level: str | None = None,
                      page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100),
                      _: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    return success_response("Predictions retrieved", data=await list_predictions(vehicle_id, risk_level, page, limit))


@router.get("/fleet-risk-summary")
async def fleet_risk_summary(_: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    return success_response("Fleet risk summary retrieved", data=await get_fleet_risk_summary())


@router.get("/predictions/{prediction_id}")
async def prediction_detail(prediction_id: str, _: dict = Depends(require_roles(PREDICTIVE_ALLOWED_ROLES))):
    data = await get_prediction_by_id(prediction_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return success_response("Prediction retrieved", data=data)
