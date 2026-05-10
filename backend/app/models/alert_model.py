from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document


ALERT_COLLECTION = "alerts"

ALERT_TYPES = {"maintenance", "vehicle", "system", "route", "demand"}
ALERT_SEVERITIES = {"info", "warning", "high", "critical"}
ALERT_STATUSES = {"active", "resolved", "dismissed"}


def build_alert_document(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "alert_type": data["alert_type"],
        "severity": data["severity"],
        "title": data["title"],
        "message": data["message"],
        "linked_vehicle_id": data.get("linked_vehicle_id"),
        "linked_part_id": data.get("linked_part_id"),
        "linked_maintenance_record_id": data.get("linked_maintenance_record_id"),
        "status": data.get("status", "active"),
        "created_by_system": data.get("created_by_system", False),
        "created_at": data.get("created_at", utc_now()),
        "resolved_at": data.get("resolved_at"),
        "resolved_by": data.get("resolved_by"),
    }


def safe_alert_document(alert: dict[str, Any] | None) -> dict[str, Any] | None:
    return serialize_mongo_document(alert)


async def ensure_alert_indexes() -> None:
    db = get_database()
    if db is None:
        return

    try:
        collection = db[ALERT_COLLECTION]
        await collection.create_index([("alert_type", ASCENDING)], name="alert_type")
        await collection.create_index([("severity", ASCENDING)], name="alert_severity")
        await collection.create_index([("status", ASCENDING)], name="alert_status")
        await collection.create_index([("linked_vehicle_id", ASCENDING)], name="alert_vehicle_id")
        await collection.create_index([("created_at", DESCENDING)], name="alert_created_at")
    except PyMongoError:
        return
