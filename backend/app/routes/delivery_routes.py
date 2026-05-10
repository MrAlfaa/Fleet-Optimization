from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.auth_middleware import require_roles
from app.models.delivery_model import DELIVERY_PRIORITIES, DELIVERY_STATUSES
from app.schemas.delivery_schema import (
    BulkDeliveryOrderCreate,
    DeliveryAssignRequest,
    DeliveryOrderCreate,
    DeliveryOrderUpdate,
    DeliveryStatusUpdateRequest,
)
from app.services.delivery_service import (
    assign_delivery_to_vehicle,
    bulk_create_delivery_orders,
    create_delivery_order,
    get_delivery_order_by_id,
    list_delivery_orders,
    update_delivery_order,
    update_delivery_status,
)
from app.services.route_prediction_service import ROUTE_ALLOWED_ROLES
from app.utils.response import success_response
from app.utils.validators import validate_choice


router = APIRouter(prefix="/deliveries", tags=["Deliveries"])


@router.get("")
async def get_deliveries(
    status: str | None = Query(default=None),
    zone_id: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    assigned_vehicle_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    if status:
        validate_choice(status, DELIVERY_STATUSES, "Delivery status")
    if priority:
        validate_choice(priority, DELIVERY_PRIORITIES, "Delivery priority")
    data = await list_delivery_orders(
        status_filter=status,
        zone_id=zone_id,
        priority=priority,
        assigned_vehicle_id=assigned_vehicle_id,
        page=page,
        limit=limit,
    )
    return success_response("Delivery orders retrieved successfully", data=data)


@router.post("")
async def add_delivery(
    payload: DeliveryOrderCreate,
    current_user: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    data = await create_delivery_order(payload.model_dump(), current_user)
    return success_response("Delivery order created successfully", data=data)


@router.post("/bulk")
async def add_deliveries_bulk(
    payload: BulkDeliveryOrderCreate,
    current_user: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    data = await bulk_create_delivery_orders([order.model_dump() for order in payload.orders], current_user)
    return success_response("Delivery orders bulk create completed", data=data)


@router.get("/{order_id}")
async def get_delivery(
    order_id: str,
    _: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    data = await get_delivery_order_by_id(order_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery order not found")
    return success_response("Delivery order retrieved successfully", data=data)


@router.put("/{order_id}")
async def edit_delivery(
    order_id: str,
    payload: DeliveryOrderUpdate,
    _: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    data = await update_delivery_order(order_id, payload.model_dump(exclude_unset=True))
    return success_response("Delivery order updated successfully", data=data)


@router.patch("/{order_id}/assign")
async def assign_delivery(
    order_id: str,
    payload: DeliveryAssignRequest,
    _: dict = Depends(require_roles(ROUTE_ALLOWED_ROLES)),
) -> dict:
    data = await assign_delivery_to_vehicle(order_id, payload.vehicle_id, payload.driver_id)
    return success_response("Delivery order assigned successfully", data=data)


@router.patch("/{order_id}/status")
async def update_status(
    order_id: str,
    payload: DeliveryStatusUpdateRequest,
    _: dict = Depends(require_roles([*ROUTE_ALLOWED_ROLES, "driver"])),
) -> dict:
    data = await update_delivery_status(order_id, payload.status)
    return success_response("Delivery order status updated successfully", data=data)
