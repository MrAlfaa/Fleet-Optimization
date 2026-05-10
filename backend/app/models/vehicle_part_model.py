from typing import Any

from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document


VEHICLE_PART_COLLECTION = "vehicle_parts"

RISK_LEVELS = {"low", "medium", "high", "critical", "unknown"}
PART_STATUSES = {"healthy", "warning", "critical", "maintained", "unknown"}

DEFAULT_EV_PARTS = [
    ("Battery Pack", "battery"),
    ("Battery Cooling System", "thermal"),
    ("Electric Motor", "powertrain"),
    ("Motor Controller", "powertrain"),
    ("Brake Pads", "braking"),
    ("Tires", "wheels"),
    ("Suspension System", "suspension"),
    ("Charging Port", "charging"),
    ("Inverter", "powertrain"),
    ("Thermal Management System", "thermal"),
]


def build_vehicle_part_document(vehicle_id: Any, data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "vehicle_id": vehicle_id,
        "part_name": data["part_name"],
        "part_category": data["part_category"],
        "risk_level": data.get("risk_level", "unknown"),
        "risk_score": float(data.get("risk_score", 0)),
        "last_serviced_date": data.get("last_serviced_date"),
        "next_predicted_maintenance_date": data.get("next_predicted_maintenance_date"),
        "status": data.get("status", "unknown"),
        "notes": data.get("notes"),
        "created_at": now,
        "updated_at": now,
    }


def safe_vehicle_part_document(part: dict[str, Any] | None) -> dict[str, Any] | None:
    return serialize_mongo_document(part)


async def ensure_vehicle_part_indexes() -> None:
    db = get_database()
    if db is None:
        return

    try:
        collection = db[VEHICLE_PART_COLLECTION]
        await collection.create_index([("vehicle_id", ASCENDING)], name="part_vehicle_id")
        await collection.create_index([("risk_level", ASCENDING)], name="part_risk_level")
        await collection.create_index([("status", ASCENDING)], name="part_status")
    except PyMongoError:
        return
