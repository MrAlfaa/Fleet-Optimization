from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import require_driver
from app.schemas.driver_schema import (
    DeliveryIncompleteRequest,
    DriverDeliveryStatusUpdateRequest,
    DriverIssueCreate,
    PostTripInspectionRequest,
    PreTripInspectionRequest,
)
from app.schemas.trip_schema import DriverLocationUpdateRequest
from app.services.driver_service import (
    acknowledge_driver_alert,
    create_driver_issue,
    get_assigned_route,
    get_assigned_vehicle,
    get_driver_alerts,
    get_delivery_attempts_for_driver,
    mark_driver_delivery_incomplete,
    update_driver_delivery_status,
)
from app.services.fleet_intelligence_service import get_driver_trip_readiness
from app.services.driver_inspection_service import (
    get_driver_inspection_status,
    submit_post_trip_inspection,
    submit_pre_trip_inspection,
)
from app.services.live_trip_service import (
    end_driver_trip,
    get_driver_trip_events,
    record_driver_location,
    start_driver_trip,
)
from app.utils.response import success_response


router = APIRouter(prefix="/driver", tags=["Driver Mobile"])


@router.get("/assigned-route")
async def assigned_route(current_user: dict = Depends(require_driver)) -> dict:
    data = await get_assigned_route(current_user)
    return success_response("Assigned route retrieved successfully", data=data)


@router.get("/assigned-vehicle")
async def assigned_vehicle(current_user: dict = Depends(require_driver)) -> dict:
    data = await get_assigned_vehicle(current_user)
    return success_response("Assigned vehicle retrieved successfully", data=data)


@router.get("/trip-readiness")
async def trip_readiness(current_user: dict = Depends(require_driver)) -> dict:
    data = await get_driver_trip_readiness(current_user)
    return success_response("Driver trip readiness evaluated successfully", data=data)


@router.get("/trips/inspection-status")
async def inspection_status(current_user: dict = Depends(require_driver)) -> dict:
    data = await get_driver_inspection_status(current_user)
    return success_response("Driver inspection status retrieved successfully", data=data)


@router.post("/trips/pre-inspection")
async def pre_trip_inspection(payload: PreTripInspectionRequest, current_user: dict = Depends(require_driver)) -> dict:
    data = await submit_pre_trip_inspection(payload.model_dump(), current_user)
    return success_response("Pre-trip vehicle inspection submitted successfully", data=data)


@router.post("/trips/post-inspection")
async def post_trip_inspection(payload: PostTripInspectionRequest, current_user: dict = Depends(require_driver)) -> dict:
    data = await submit_post_trip_inspection(payload.model_dump(), current_user)
    return success_response("Post-trip vehicle inspection submitted successfully", data=data)


@router.get("/alerts")
async def driver_alerts(current_user: dict = Depends(require_driver)) -> dict:
    data = await get_driver_alerts(current_user)
    return success_response("Driver alerts retrieved successfully", data=data)


@router.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, current_user: dict = Depends(require_driver)) -> dict:
    data = await acknowledge_driver_alert(alert_id, current_user)
    return success_response("Driver alert acknowledged successfully", data=data)


@router.patch("/deliveries/{order_id}/status")
async def update_delivery_status(
    order_id: str,
    payload: DriverDeliveryStatusUpdateRequest,
    current_user: dict = Depends(require_driver),
) -> dict:
    data = await update_driver_delivery_status(order_id, payload.status, current_user)
    return success_response("Delivery status updated successfully", data=data)


@router.post("/deliveries/{order_id}/incomplete")
async def incomplete_delivery(order_id: str, payload: DeliveryIncompleteRequest, current_user: dict = Depends(require_driver)) -> dict:
    data = await mark_driver_delivery_incomplete(order_id, payload.model_dump(), current_user)
    return success_response("Delivery rescheduled for the next day", data=data)


@router.get("/deliveries/{order_id}/attempts")
async def delivery_attempts(order_id: str, current_user: dict = Depends(require_driver)) -> dict:
    return success_response("Delivery attempts retrieved successfully", data=await get_delivery_attempts_for_driver(order_id, current_user))


@router.post("/issues")
async def report_issue(payload: DriverIssueCreate, current_user: dict = Depends(require_driver)) -> dict:
    data = await create_driver_issue(payload.model_dump(), current_user)
    return success_response("Driver issue reported successfully", data=data)


@router.post("/trips/start")
async def start_trip(current_user: dict = Depends(require_driver)) -> dict:
    data = await start_driver_trip(current_user)
    return success_response("Driver trip started successfully", data=data)


@router.post("/trips/end")
async def end_trip(current_user: dict = Depends(require_driver)) -> dict:
    data = await end_driver_trip(current_user)
    return success_response("Driver trip ended successfully", data=data)


@router.post("/location")
async def update_location(
    payload: DriverLocationUpdateRequest,
    current_user: dict = Depends(require_driver),
) -> dict:
    data = await record_driver_location(payload.model_dump(), current_user)
    return success_response("Driver location recorded successfully", data=data)


@router.get("/trip-events")
async def trip_events(current_user: dict = Depends(require_driver)) -> dict:
    data = await get_driver_trip_events(current_user)
    return success_response("Driver trip events retrieved successfully", data=data)
