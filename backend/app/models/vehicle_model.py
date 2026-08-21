from datetime import datetime
from typing import Any

from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document


VEHICLE_COLLECTION = "vehicles"

VEHICLE_STATUSES = {"active", "inactive", "under_maintenance", "retired"}
VEHICLE_HEALTH_STATUSES = {"healthy", "warning", "critical", "unknown"}
VEHICLE_TYPES = {"electric_van", "electric_truck", "electric_car", "electric_bus", "other"}
FUEL_TYPES = {"electric", "hybrid", "diesel", "petrol"}


def build_vehicle_document(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "vehicle_code": data["vehicle_code"].upper(),
        "registration_number": data["registration_number"].upper(),
        "vehicle_type": data["vehicle_type"],
        "brand": data["brand"],
        "model": data["model"],
        "year": data["year"],
        "fuel_type": data["fuel_type"],
        "current_mileage": float(data.get("current_mileage", 0)),
        "battery_capacity_kwh": data.get("battery_capacity_kwh"),
        "image_url": data.get("image_url"),
        "assigned_driver_id": data.get("assigned_driver_id"),
        "status": data.get("status", "active"),
        "health_status": data.get("health_status", "unknown"),
        "last_service_date": data.get("last_service_date"),
        "next_service_due_date": data.get("next_service_due_date"),
        "retired_at": None,
        "retired_by": None,
        "retirement_reason": None,
        "created_at": now,
        "updated_at": now,
    }


def safe_vehicle_document(vehicle: dict[str, Any] | None) -> dict[str, Any] | None:
    return serialize_mongo_document(vehicle)


async def ensure_vehicle_indexes() -> None:
    db = get_database()
    if db is None:
        return

    try:
        collection = db[VEHICLE_COLLECTION]
        await collection.create_index([("vehicle_code", ASCENDING)], unique=True, name="unique_vehicle_code")
        await collection.create_index([("registration_number", ASCENDING)], unique=True, name="unique_registration_number")
        await collection.create_index([("status", ASCENDING)], name="vehicle_status")
        await collection.create_index([("health_status", ASCENDING)], name="vehicle_health_status")
        await collection.create_index([("assigned_driver_id", ASCENDING)], name="vehicle_assigned_driver")
    except PyMongoError:
        return
