from typing import Any

from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION, build_alert_document, safe_alert_document
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_list, validate_object_id
from app.utils.pagination import build_pagination_response, calculate_skip, normalize_pagination


def get_alert_collection():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db[ALERT_COLLECTION]


def _convert_optional_id(data: dict[str, Any], field: str, label: str) -> None:
    if data.get(field):
        try:
            data[field] = validate_object_id(data[field])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {label}") from exc


async def create_alert(data: dict[str, Any]) -> dict[str, Any]:
    prepared = data.copy()
    _convert_optional_id(prepared, "linked_vehicle_id", "vehicle ID")
    _convert_optional_id(prepared, "linked_part_id", "part ID")
    _convert_optional_id(prepared, "linked_maintenance_record_id", "maintenance record ID")
    _convert_optional_id(prepared, "linked_prediction_review_id", "prediction review ID")
    _convert_optional_id(prepared, "resolved_by", "resolver user ID")

    document = build_alert_document(prepared)
    result = await get_alert_collection().insert_one(document)
    return safe_alert_document(await get_alert_collection().find_one({"_id": result.inserted_id}))


async def list_alerts(
    alert_type: str | None = None,
    severity: str | None = None,
    status_filter: str | None = None,
    vehicle_id: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    query: dict[str, Any] = {}
    if alert_type:
        query["alert_type"] = alert_type
    if severity:
        query["severity"] = severity
    if status_filter:
        query["status"] = status_filter
    if vehicle_id:
        try:
            query["linked_vehicle_id"] = validate_object_id(vehicle_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle ID") from exc

    collection = get_alert_collection()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("created_at", -1).skip(calculate_skip(page, limit)).limit(limit)
    return build_pagination_response(serialize_mongo_list(await cursor.to_list(length=limit)), total, page, limit)


async def get_alert_by_id(alert_id: str) -> dict[str, Any] | None:
    try:
        object_id = validate_object_id(alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid alert ID") from exc
    return safe_alert_document(await get_alert_collection().find_one({"_id": object_id}))


async def _update_alert_status(alert_id: str, status_value: str, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        object_id = validate_object_id(alert_id)
        user_id = validate_object_id(current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid alert or user ID") from exc

    update = {"status": status_value, "resolved_at": utc_now(), "resolved_by": user_id}
    result = await get_alert_collection().update_one({"_id": object_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return safe_alert_document(await get_alert_collection().find_one({"_id": object_id}))


async def resolve_alert(alert_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    return await _update_alert_status(alert_id, "resolved", current_user)


async def dismiss_alert(alert_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    return await _update_alert_status(alert_id, "dismissed", current_user)


async def create_maintenance_alert(
    vehicle_id: str,
    part_id: str | None,
    severity: str,
    message: str,
    maintenance_record_id: str | None = None,
) -> dict[str, Any]:
    return await create_alert(
        {
            "alert_type": "maintenance",
            "severity": severity,
            "title": "Maintenance attention required",
            "message": message,
            "linked_vehicle_id": vehicle_id,
            "linked_part_id": part_id,
            "linked_maintenance_record_id": maintenance_record_id,
            "created_by_system": True,
        }
    )


async def get_active_alert_count() -> int:
    return await get_alert_collection().count_documents({"status": "active"})


async def get_alert_summary() -> dict[str, int]:
    collection = get_alert_collection()
    return {
        "active": await collection.count_documents({"status": "active"}),
        "resolved": await collection.count_documents({"status": "resolved"}),
        "dismissed": await collection.count_documents({"status": "dismissed"}),
        "critical": await collection.count_documents({"severity": "critical"}),
        "high": await collection.count_documents({"severity": "high"}),
        "warning": await collection.count_documents({"severity": "warning"}),
        "info": await collection.count_documents({"severity": "info"}),
    }
