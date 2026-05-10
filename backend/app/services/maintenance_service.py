import re
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.maintenance_model import MAINTENANCE_COLLECTION, build_maintenance_document, safe_maintenance_document
from app.models.user_model import utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.models.vehicle_part_model import VEHICLE_PART_COLLECTION
from app.services.alert_service import create_maintenance_alert
from app.services.vehicle_part_service import reset_part_after_maintenance
from app.utils.object_id import serialize_mongo_list, validate_object_id
from app.utils.pagination import build_pagination_response, calculate_skip, normalize_pagination


def get_maintenance_collection():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db[MAINTENANCE_COLLECTION]


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db


async def _prepare_record_data(data: dict[str, Any]) -> dict[str, Any]:
    prepared = data.copy()
    try:
        prepared["vehicle_id"] = validate_object_id(prepared["vehicle_id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle ID") from exc

    vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": prepared["vehicle_id"]})
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    if prepared.get("part_id"):
        try:
            prepared["part_id"] = validate_object_id(prepared["part_id"])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid part ID") from exc
        part = await _db()[VEHICLE_PART_COLLECTION].find_one({"_id": prepared["part_id"], "vehicle_id": prepared["vehicle_id"]})
        if part is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle part not found")
    return prepared


async def create_maintenance_record(data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    prepared = await _prepare_record_data(data)
    try:
        created_by = validate_object_id(current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID") from exc

    document = build_maintenance_document(prepared, created_by)
    result = await get_maintenance_collection().insert_one(document)
    created = await get_maintenance_collection().find_one({"_id": result.inserted_id})

    if created["priority"] in {"high", "critical"}:
        severity = "critical" if created["priority"] == "critical" else "high"
        await create_maintenance_alert(
            str(created["vehicle_id"]),
            str(created["part_id"]) if created.get("part_id") else None,
            severity,
            f"{created['priority'].title()} priority {created['maintenance_type']} maintenance scheduled for {created['part_name']}.",
            str(created["_id"]),
        )

    return safe_maintenance_document(created)


async def list_maintenance_records(
    vehicle_id: str | None = None,
    status_filter: str | None = None,
    priority: str | None = None,
    maintenance_type: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    query: dict[str, Any] = {}
    if vehicle_id:
        try:
            query["vehicle_id"] = validate_object_id(vehicle_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle ID") from exc
    if status_filter:
        query["status"] = status_filter
    if priority:
        query["priority"] = priority
    if maintenance_type:
        query["maintenance_type"] = maintenance_type
    if search:
        search_regex = re.compile(re.escape(search), re.IGNORECASE)
        query["$or"] = [{"part_name": search_regex}, {"issue_type": search_regex}, {"notes": search_regex}]

    collection = get_maintenance_collection()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("service_date", -1).skip(calculate_skip(page, limit)).limit(limit)
    return build_pagination_response(serialize_mongo_list(await cursor.to_list(length=limit)), total, page, limit)


async def get_maintenance_record_by_id(record_id: str) -> dict[str, Any] | None:
    try:
        object_id = validate_object_id(record_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid maintenance record ID") from exc
    return safe_maintenance_document(await get_maintenance_collection().find_one({"_id": object_id}))


async def update_maintenance_record(record_id: str, data: dict[str, Any]) -> dict[str, Any]:
    try:
        object_id = validate_object_id(record_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid maintenance record ID") from exc

    update_data = {key: value for key, value in data.items() if value is not None}
    if "part_id" in update_data and update_data["part_id"]:
        try:
            update_data["part_id"] = validate_object_id(update_data["part_id"])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid part ID") from exc
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")
    update_data["updated_at"] = utc_now()
    result = await get_maintenance_collection().update_one({"_id": object_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found")
    return safe_maintenance_document(await get_maintenance_collection().find_one({"_id": object_id}))


async def complete_maintenance_record(record_id: str, completion_data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        object_id = validate_object_id(record_id)
        resolver_id = validate_object_id(current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID") from exc

    record = await get_maintenance_collection().find_one({"_id": object_id})
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found")

    now = utc_now()
    update_data = {key: value for key, value in completion_data.items() if value is not None}
    update_data.update({"status": "completed", "updated_at": now})
    await get_maintenance_collection().update_one({"_id": object_id}, {"$set": update_data})
    await _db()[VEHICLE_COLLECTION].update_one(
        {"_id": record["vehicle_id"]},
        {"$set": {"last_service_date": record["service_date"], "updated_at": now}},
    )

    if record.get("part_id"):
        await _db()[VEHICLE_PART_COLLECTION].update_one(
            {"_id": record["part_id"]},
            {"$set": {"last_serviced_date": record["service_date"], "updated_at": now}},
        )
        await reset_part_after_maintenance(str(record["part_id"]))

    alert_update = {
        "$set": {
            "status": "resolved",
            "resolved_at": now,
            "resolved_by": resolver_id,
        }
    }
    result = await _db()[ALERT_COLLECTION].update_many(
        {"linked_maintenance_record_id": object_id, "status": "active"},
        alert_update,
    )
    if result.matched_count == 0:
        await create_maintenance_alert(
            str(record["vehicle_id"]),
            str(record["part_id"]) if record.get("part_id") else None,
            "info",
            f"Maintenance completed for {record['part_name']}.",
            str(record["_id"]),
        )
        await _db()[ALERT_COLLECTION].update_one(
            {"linked_maintenance_record_id": object_id, "message": f"Maintenance completed for {record['part_name']}."},
            alert_update,
        )

    return safe_maintenance_document(await get_maintenance_collection().find_one({"_id": object_id}))


async def cancel_maintenance_record(record_id: str) -> dict[str, Any]:
    return await update_maintenance_record(record_id, {"status": "cancelled"})


async def get_maintenance_summary() -> dict[str, int]:
    collection = get_maintenance_collection()
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return {
        "scheduled": await collection.count_documents({"status": "scheduled"}),
        "in_progress": await collection.count_documents({"status": "in_progress"}),
        "completed": await collection.count_documents({"status": "completed"}),
        "cancelled": await collection.count_documents({"status": "cancelled"}),
        "high_priority": await collection.count_documents({"priority": "high"}),
        "critical_priority": await collection.count_documents({"priority": "critical"}),
        "completed_this_month": await collection.count_documents({"status": "completed", "service_date": {"$gte": month_start}}),
    }
