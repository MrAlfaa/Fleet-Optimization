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
FUEL_TYPES = {"electric", "hybrid", "diesel", "petrol"}
VEHICLE_CATEGORIES = {"car", "van", "truck", "bus"}
VEHICLE_ONBOARDING_TYPES = {"brand_new", "existing_fleet"}
VEHICLE_COMMISSIONING_STATUSES = {"not_started", "pending", "passed", "failed"}
VEHICLE_TYPES = {
    f"{fuel_type}_{category}"
    for fuel_type in FUEL_TYPES
    for category in VEHICLE_CATEGORIES
} | {"other"}


def infer_vehicle_category(data: dict[str, Any]) -> str:
    category = str(data.get("vehicle_category") or "").lower()
    if category in VEHICLE_CATEGORIES:
        return category
    vehicle_type = str(data.get("vehicle_type") or "").lower()
    for candidate in VEHICLE_CATEGORIES:
        if candidate in vehicle_type:
            return candidate
    return "van"


def build_vehicle_document(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "vehicle_code": data["vehicle_code"].upper(),
        "registration_number": data["registration_number"].upper(),
        "vehicle_type": data["vehicle_type"],
        "vehicle_category": infer_vehicle_category(data),
        "brand": data["brand"],
        "model": data["model"],
        "year": data["year"],
        "fuel_type": data["fuel_type"],
        "current_mileage": float(data.get("current_mileage", 0)),
        "in_service_date": data.get("in_service_date"),
        "payload_capacity_kg": data.get("payload_capacity_kg"),
        "load_profile": data.get("load_profile"),
        "battery_capacity_kwh": data.get("battery_capacity_kwh"),
        "image_url": data.get("image_url"),
        "assigned_driver_id": data.get("assigned_driver_id"),
        "status": "inactive",
        "health_status": data.get("health_status", "unknown"),
        "onboarding_type": data.get("onboarding_type", "existing_fleet"),
        "commissioning_status": "not_started",
        "history_tracking_started_at": now,
        "latest_assessment_risk": data.get("latest_assessment_risk"),
        "latest_assessment_at": data.get("latest_assessment_at"),
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
