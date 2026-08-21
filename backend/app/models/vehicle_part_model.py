from typing import Any

from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document


VEHICLE_PART_COLLECTION = "vehicle_parts"

RISK_LEVELS = {"low", "medium", "high", "critical", "unknown"}
PART_STATUSES = {"healthy", "warning", "critical", "maintained", "unknown"}

EV_PART_CATALOG = [
    {"key": "battery_pack", "name": "Battery Pack", "category": "battery", "description": "High-voltage traction battery assembly", "ml_supported": True, "ml_signal_group": "battery"},
    {"key": "battery_cooling", "name": "Battery Cooling System", "category": "thermal", "description": "Battery coolant circulation and temperature control", "ml_supported": True, "ml_signal_group": "thermal"},
    {"key": "electric_motor", "name": "Electric Motor", "category": "powertrain", "description": "Electric traction motor and monitored operating condition", "ml_supported": True, "ml_signal_group": "motor"},
    {"key": "motor_controller", "name": "Motor Controller", "category": "powertrain", "description": "Traction motor control electronics", "ml_supported": True, "ml_signal_group": "motor"},
    {"key": "brake_pads", "name": "Brake Pads", "category": "braking", "description": "Friction brake wear components", "ml_supported": True, "ml_signal_group": "braking"},
    {"key": "tires", "name": "Tires", "category": "wheels", "description": "Road tires monitored for pressure and temperature", "ml_supported": True, "ml_signal_group": "tires"},
    {"key": "suspension", "name": "Suspension System", "category": "suspension", "description": "Load-bearing suspension and ride components", "ml_supported": True, "ml_signal_group": "suspension"},
    {"key": "charging_port", "name": "Charging Port", "category": "charging", "description": "Vehicle charging inlet and connection hardware", "ml_supported": True, "ml_signal_group": "charging"},
    {"key": "inverter", "name": "Inverter", "category": "powertrain", "description": "High-voltage power conversion for the traction motor", "ml_supported": True, "ml_signal_group": "motor"},
    {"key": "thermal_management", "name": "Thermal Management System", "category": "thermal", "description": "Vehicle-wide battery and motor thermal control", "ml_supported": True, "ml_signal_group": "thermal"},
]

DEFAULT_EV_PARTS = [(item["name"], item["category"]) for item in EV_PART_CATALOG]


def get_ev_part_catalog() -> list[dict[str, Any]]:
    return [dict(item) for item in EV_PART_CATALOG]


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
        "is_active": bool(data.get("is_active", True)),
        "archived_at": None,
        "archived_by": None,
        "archive_reason": None,
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
        await collection.create_index([("vehicle_id", ASCENDING), ("part_name", ASCENDING)], name="part_vehicle_name")
    except PyMongoError:
        return
