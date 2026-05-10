from typing import Any

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.database import get_database
from app.models.delivery_model import DELIVERY_COLLECTION, build_delivery_order_document, safe_delivery_document
from app.models.user_model import utc_now
from app.services.user_service import get_raw_user_by_id
from app.services.vehicle_service import get_vehicle_by_id
from app.utils.geo_utils import validate_coordinates
from app.utils.object_id import serialize_mongo_list, validate_object_id
from app.utils.pagination import build_pagination_response, calculate_skip, normalize_pagination


def get_delivery_collection():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db[DELIVERY_COLLECTION]


async def _validate_vehicle_driver_ids(data: dict[str, Any]) -> dict[str, Any]:
    prepared = data.copy()
    if prepared.get("assigned_vehicle_id"):
        vehicle = await get_vehicle_by_id(prepared["assigned_vehicle_id"])
        if vehicle is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned vehicle does not exist")
        prepared["assigned_vehicle_id"] = validate_object_id(prepared["assigned_vehicle_id"])
    if prepared.get("assigned_driver_id"):
        driver_id = validate_object_id(prepared["assigned_driver_id"])
        driver = await get_raw_user_by_id(str(driver_id))
        if driver is None or driver.get("role") != "driver":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned driver must be an existing driver")
        prepared["assigned_driver_id"] = driver_id
    return prepared


def _validate_delivery_coordinates(data: dict[str, Any]) -> None:
    pickup_lat = data.get("pickup_latitude")
    pickup_lon = data.get("pickup_longitude")
    drop_lat = data.get("drop_latitude")
    drop_lon = data.get("drop_longitude")
    if pickup_lat is not None and pickup_lon is not None:
        validate_coordinates(pickup_lat, pickup_lon)
    if drop_lat is not None and drop_lon is not None:
        validate_coordinates(drop_lat, drop_lon)


async def create_delivery_order(data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    _validate_delivery_coordinates(data)
    prepared = await _validate_vehicle_driver_ids(data)
    document = build_delivery_order_document(prepared)
    try:
        result = await get_delivery_collection().insert_one(document)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Delivery order code already exists") from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database operation failed") from exc
    return safe_delivery_document(await get_delivery_collection().find_one({"_id": result.inserted_id}))


async def bulk_create_delivery_orders(order_list: list[dict[str, Any]], current_user: dict[str, Any]) -> dict[str, Any]:
    created: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for order in order_list:
        try:
            created.append(await create_delivery_order(order, current_user))
        except HTTPException as exc:
            skipped.append({"order_code": order.get("order_code") or "", "reason": str(exc.detail)})
    return {"created_count": len(created), "skipped_count": len(skipped), "items": created, "skipped": skipped}


async def list_delivery_orders(
    status_filter: str | None = None,
    zone_id: str | None = None,
    priority: str | None = None,
    assigned_vehicle_id: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    query: dict[str, Any] = {}
    if status_filter:
        query["delivery_status"] = status_filter
    if zone_id:
        query["zone_id"] = zone_id
    if priority:
        query["priority"] = priority
    if assigned_vehicle_id:
        query["assigned_vehicle_id"] = validate_object_id(assigned_vehicle_id)

    collection = get_delivery_collection()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("created_at", -1).skip(calculate_skip(page, limit)).limit(limit)
    return build_pagination_response(serialize_mongo_list(await cursor.to_list(length=limit)), total, page, limit)


async def get_delivery_order_by_id(order_id: str) -> dict[str, Any] | None:
    try:
        object_id = validate_object_id(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid delivery order ID") from exc
    return safe_delivery_document(await get_delivery_collection().find_one({"_id": object_id}))


async def get_raw_delivery_order_by_id(order_id: str) -> dict[str, Any] | None:
    try:
        object_id = validate_object_id(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid delivery order ID") from exc
    return await get_delivery_collection().find_one({"_id": object_id})


async def update_delivery_order(order_id: str, data: dict[str, Any]) -> dict[str, Any]:
    try:
        object_id = validate_object_id(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid delivery order ID") from exc
    update_data = {key: value for key, value in data.items() if value is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")
    _validate_delivery_coordinates(update_data)
    update_data = await _validate_vehicle_driver_ids(update_data)
    update_data["updated_at"] = utc_now()
    try:
        result = await get_delivery_collection().update_one({"_id": object_id}, {"$set": update_data})
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Delivery order code already exists") from exc
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery order not found")
    return safe_delivery_document(await get_delivery_collection().find_one({"_id": object_id}))


async def assign_delivery_to_vehicle(order_id: str, vehicle_id: str, driver_id: str | None = None) -> dict[str, Any]:
    payload = {"assigned_vehicle_id": vehicle_id, "delivery_status": "assigned"}
    if driver_id:
        payload["assigned_driver_id"] = driver_id
    return await update_delivery_order(order_id, payload)


async def update_delivery_status(order_id: str, status_value: str) -> dict[str, Any]:
    return await update_delivery_order(order_id, {"delivery_status": status_value})
