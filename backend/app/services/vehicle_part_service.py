import re
from typing import Any

from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.user_model import utc_now
from app.models.vehicle_part_model import (
    DEFAULT_EV_PARTS,
    VEHICLE_PART_COLLECTION,
    build_vehicle_part_document,
    safe_vehicle_part_document,
)
from app.utils.object_id import serialize_mongo_list, validate_object_id


def get_vehicle_part_collection():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db[VEHICLE_PART_COLLECTION]


async def create_vehicle_part(vehicle_id: str, data: dict[str, Any]) -> dict[str, Any]:
    try:
        vehicle_object_id = validate_object_id(vehicle_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle ID") from exc

    duplicate = await get_vehicle_part_collection().find_one({"vehicle_id": vehicle_object_id, "part_name": {"$regex": f"^{re.escape(data['part_name'])}$", "$options": "i"}, "is_active": {"$ne": False}})
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An active part with this name already exists")
    document = build_vehicle_part_document(vehicle_object_id, data)
    result = await get_vehicle_part_collection().insert_one(document)
    created = await get_vehicle_part_collection().find_one({"_id": result.inserted_id})
    return safe_vehicle_part_document(created)


async def get_parts_by_vehicle(vehicle_id: str, include_archived: bool = False) -> list[dict[str, Any]]:
    try:
        vehicle_object_id = validate_object_id(vehicle_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle ID") from exc

    query = {"vehicle_id": vehicle_object_id}
    if not include_archived:
        query["is_active"] = {"$ne": False}
    cursor = get_vehicle_part_collection().find(query).sort("part_name", 1)
    return serialize_mongo_list(await cursor.to_list(length=200))


async def get_part_by_id(part_id: str) -> dict[str, Any] | None:
    try:
        object_id = validate_object_id(part_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid part ID") from exc

    return safe_vehicle_part_document(await get_vehicle_part_collection().find_one({"_id": object_id}))


async def update_vehicle_part(part_id: str, data: dict[str, Any]) -> dict[str, Any]:
    try:
        object_id = validate_object_id(part_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid part ID") from exc

    update_data = {key: value for key, value in data.items() if value is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")
    update_data["updated_at"] = utc_now()

    result = await get_vehicle_part_collection().update_one({"_id": object_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle part not found")

    return safe_vehicle_part_document(await get_vehicle_part_collection().find_one({"_id": object_id}))


async def update_part_risk(part_id: str, risk_score: float, risk_level: str, status_value: str) -> dict[str, Any]:
    return await update_vehicle_part(
        part_id,
        {"risk_score": risk_score, "risk_level": risk_level, "status": status_value},
    )


async def reset_part_after_maintenance(part_id: str) -> dict[str, Any]:
    return await update_part_risk(part_id, 0, "low", "maintained")


async def archive_vehicle_part(part_id: str, current_user: dict[str, Any], reason: str | None = None) -> dict[str, Any]:
    object_id = validate_object_id(part_id)
    db = get_database()
    open_record = await db["maintenance_records"].find_one({"part_id": object_id, "status": {"$in": ["scheduled", "in_progress"]}})
    if open_record:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancel or complete open maintenance before archiving this part")
    result = await get_vehicle_part_collection().update_one({"_id": object_id, "is_active": {"$ne": False}}, {"$set": {
        "is_active": False, "archived_at": utc_now(), "archived_by": validate_object_id(current_user["id"]), "archive_reason": reason, "updated_at": utc_now(),
    }})
    if not result.matched_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active vehicle part not found")
    return safe_vehicle_part_document(await get_vehicle_part_collection().find_one({"_id": object_id}))


async def restore_vehicle_part(part_id: str) -> dict[str, Any]:
    object_id = validate_object_id(part_id)
    part = await get_vehicle_part_collection().find_one({"_id": object_id})
    if not part or part.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only archived parts can be restored")
    duplicate = await get_vehicle_part_collection().find_one({"vehicle_id": part["vehicle_id"], "part_name": {"$regex": f"^{re.escape(part['part_name'])}$", "$options": "i"}, "is_active": {"$ne": False}, "_id": {"$ne": object_id}})
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An active part with this name already exists")
    await get_vehicle_part_collection().update_one({"_id": object_id}, {"$set": {"is_active": True, "archived_at": None, "archived_by": None, "archive_reason": None, "updated_at": utc_now()}})
    return safe_vehicle_part_document(await get_vehicle_part_collection().find_one({"_id": object_id}))


async def create_default_parts_for_vehicle(vehicle_id: str) -> list[dict[str, Any]]:
    existing = await get_parts_by_vehicle(vehicle_id)
    existing_names = {part["part_name"] for part in existing}
    created_parts: list[dict[str, Any]] = []

    for part_name, part_category in DEFAULT_EV_PARTS:
        if part_name in existing_names:
            continue
        created_parts.append(
            await create_vehicle_part(
                vehicle_id,
                {
                    "part_name": part_name,
                    "part_category": part_category,
                    "risk_level": "unknown",
                    "risk_score": 0,
                    "status": "unknown",
                },
            )
        )

    return created_parts
