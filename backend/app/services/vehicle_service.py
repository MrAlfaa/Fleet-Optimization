import re
from typing import Any

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION, build_vehicle_document, safe_vehicle_document
from app.services.user_service import get_raw_user_by_id
from app.services.vehicle_part_service import create_default_parts_for_vehicle
from app.utils.object_id import serialize_mongo_list, validate_object_id
from app.utils.pagination import build_pagination_response, calculate_skip, normalize_pagination


def get_vehicle_collection():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db[VEHICLE_COLLECTION]


async def _prepare_vehicle_data(data: dict[str, Any]) -> dict[str, Any]:
    prepared = data.copy()
    if prepared.get("assigned_driver_id"):
        try:
            driver_id = validate_object_id(prepared["assigned_driver_id"])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid driver ID") from exc
        driver = await get_raw_user_by_id(str(driver_id))
        if driver is None or driver.get("role") != "driver":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned driver must be an existing driver user")
        prepared["assigned_driver_id"] = driver_id
    return prepared


async def create_vehicle(data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    prepared = await _prepare_vehicle_data(data)
    document = build_vehicle_document(prepared)

    try:
        result = await get_vehicle_collection().insert_one(document)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vehicle code or registration number already exists") from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database operation failed") from exc

    created = await get_vehicle_collection().find_one({"_id": result.inserted_id})
    await create_default_parts_for_vehicle(str(result.inserted_id))
    return safe_vehicle_document(created)


async def get_vehicle_by_id(vehicle_id: str) -> dict[str, Any] | None:
    try:
        object_id = validate_object_id(vehicle_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle ID") from exc
    return safe_vehicle_document(await get_vehicle_collection().find_one({"_id": object_id}))


async def get_vehicle_by_code(vehicle_code: str) -> dict[str, Any] | None:
    return safe_vehicle_document(await get_vehicle_collection().find_one({"vehicle_code": vehicle_code.upper()}))


async def list_vehicles(
    status_filter: str | None = None,
    health_status: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    query: dict[str, Any] = {}
    if status_filter:
        query["status"] = status_filter
    if health_status:
        query["health_status"] = health_status
    if search:
        search_regex = re.compile(re.escape(search), re.IGNORECASE)
        query["$or"] = [
            {"vehicle_code": search_regex},
            {"registration_number": search_regex},
            {"brand": search_regex},
            {"model": search_regex},
        ]

    collection = get_vehicle_collection()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("created_at", -1).skip(calculate_skip(page, limit)).limit(limit)
    items = serialize_mongo_list(await cursor.to_list(length=limit))
    return build_pagination_response(items, total, page, limit)


async def update_vehicle(vehicle_id: str, data: dict[str, Any]) -> dict[str, Any]:
    try:
        object_id = validate_object_id(vehicle_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle ID") from exc

    update_data = {key: value for key, value in data.items() if value is not None}
    if "assigned_driver_id" in update_data and update_data["assigned_driver_id"]:
        update_data = await _prepare_vehicle_data(update_data)
    if "vehicle_code" in update_data:
        update_data["vehicle_code"] = update_data["vehicle_code"].upper()
    if "registration_number" in update_data:
        update_data["registration_number"] = update_data["registration_number"].upper()
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")
    update_data["updated_at"] = utc_now()

    try:
        result = await get_vehicle_collection().update_one({"_id": object_id}, {"$set": update_data})
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vehicle code or registration number already exists") from exc

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return safe_vehicle_document(await get_vehicle_collection().find_one({"_id": object_id}))


async def retire_vehicle(vehicle_id: str, current_user: dict[str, Any] | None = None, reason: str | None = None) -> dict[str, Any]:
    object_id = validate_object_id(vehicle_id)
    active_route = await _database()["route_plans"].find_one({
        "vehicle_id": object_id,
        "status": {"$in": ["dispatched", "in_progress"]},
    })
    if active_route:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancel or complete the active route before retiring this vehicle")
    now = utc_now()
    update = {
        "status": "retired", "assigned_driver_id": None, "retired_at": now,
        "retired_by": validate_object_id(current_user["id"]) if current_user else None,
        "retirement_reason": reason, "updated_at": now,
    }
    result = await get_vehicle_collection().update_one({"_id": object_id}, {"$set": update})
    if not result.matched_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return safe_vehicle_document(await get_vehicle_collection().find_one({"_id": object_id}))


async def restore_vehicle(vehicle_id: str) -> dict[str, Any]:
    object_id = validate_object_id(vehicle_id)
    result = await get_vehicle_collection().update_one(
        {"_id": object_id, "status": "retired"},
        {"$set": {"status": "inactive", "retired_at": None, "retired_by": None, "retirement_reason": None, "updated_at": utc_now()}},
    )
    if not result.matched_count:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only retired vehicles can be restored")
    return safe_vehicle_document(await get_vehicle_collection().find_one({"_id": object_id}))


async def delete_vehicle(vehicle_id: str) -> dict[str, Any]:
    return await retire_vehicle(vehicle_id)


def _database():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db


async def assign_driver(vehicle_id: str, driver_id: str) -> dict[str, Any]:
    return await update_vehicle(vehicle_id, {"assigned_driver_id": driver_id})


async def get_vehicle_summary() -> dict[str, int]:
    collection = get_vehicle_collection()
    return {
        "total_vehicles": await collection.count_documents({}),
        "active_vehicles": await collection.count_documents({"status": "active"}),
        "under_maintenance": await collection.count_documents({"status": "under_maintenance"}),
        "critical_vehicles": await collection.count_documents({"health_status": "critical"}),
    }
