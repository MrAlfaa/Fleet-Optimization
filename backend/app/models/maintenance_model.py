from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document


MAINTENANCE_COLLECTION = "maintenance_records"

MAINTENANCE_TYPES = {"preventive", "corrective", "predictive", "inspection", "replacement"}
MAINTENANCE_STATUSES = {"scheduled", "in_progress", "completed", "cancelled"}
MAINTENANCE_PRIORITIES = {"low", "medium", "high", "critical"}


def build_maintenance_document(data: dict[str, Any], created_by: Any) -> dict[str, Any]:
    now = utc_now()
    return {
        "vehicle_id": data["vehicle_id"],
        "part_id": data.get("part_id"),
        "part_name": data["part_name"],
        "maintenance_type": data["maintenance_type"],
        "issue_type": data["issue_type"],
        "service_date": data["service_date"],
        "mileage_at_service": float(data["mileage_at_service"]),
        "technician_name": data.get("technician_name"),
        "service_center": data.get("service_center"),
        "cost": data.get("cost"),
        "status": data.get("status", "scheduled"),
        "priority": data.get("priority", "medium"),
        "notes": data.get("notes"),
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }


def safe_maintenance_document(record: dict[str, Any] | None) -> dict[str, Any] | None:
    return serialize_mongo_document(record)


async def ensure_maintenance_indexes() -> None:
    db = get_database()
    if db is None:
        return

    try:
        collection = db[MAINTENANCE_COLLECTION]
        await collection.create_index([("vehicle_id", ASCENDING)], name="maintenance_vehicle_id")
        await collection.create_index([("part_id", ASCENDING)], name="maintenance_part_id")
        await collection.create_index([("status", ASCENDING)], name="maintenance_status")
        await collection.create_index([("priority", ASCENDING)], name="maintenance_priority")
        await collection.create_index([("maintenance_type", ASCENDING)], name="maintenance_type")
        await collection.create_index([("service_date", DESCENDING)], name="maintenance_service_date")
    except PyMongoError:
        return
