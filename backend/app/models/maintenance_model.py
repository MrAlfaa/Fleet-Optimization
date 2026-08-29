from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.models.inspection_model import WORK_ORDER_INDEXES
from app.utils.object_id import serialize_mongo_document


MAINTENANCE_COLLECTION = "maintenance_records"

MAINTENANCE_TYPES = {"preventive", "corrective", "predictive", "inspection", "replacement"}
MAINTENANCE_STATUSES = {"scheduled", "in_progress", "completed", "cancelled"}
MAINTENANCE_PRIORITIES = {"low", "medium", "high", "critical"}
MAINTENANCE_SYSTEMS = {
    "battery_system", "braking", "charging_system", "cooling_system", "electrical",
    "engine", "exhaust_dpf", "fuel_system", "ignition", "motor_drivetrain",
    "steering", "suspension", "thermal_system", "tires",
}
MAINTENANCE_EVENT_KINDS = {"scheduled_service", "corrective_repair", "breakdown", "inspection"}


def build_maintenance_document(data: dict[str, Any], created_by: Any) -> dict[str, Any]:
    now = utc_now()
    return {
        "vehicle_id": data["vehicle_id"],
        "part_id": data.get("part_id"),
        "part_name": data["part_name"],
        "maintenance_type": data["maintenance_type"],
        "maintenance_system": data.get("maintenance_system"),
        "event_kind": data.get("event_kind"),
        "issue_type": data["issue_type"],
        "service_date": data["service_date"],
        "mileage_at_service": float(data["mileage_at_service"]),
        "technician_name": data.get("technician_name"),
        "service_center": data.get("service_center"),
        "cost": data.get("cost"),
        "status": data.get("status", "scheduled"),
        "priority": data.get("priority", "medium"),
        "notes": data.get("notes"),
        "prediction_review_id": data.get("prediction_review_id"),
        "inspection_id": data.get("inspection_id"),
        "assessment_id": data.get("assessment_id"),
        "work_order_status": data.get("work_order_status", "planned"),
        "estimated_cost": data.get("estimated_cost"),
        "actual_cost": data.get("actual_cost"),
        "approved_by": data.get("approved_by"),
        "approved_at": data.get("approved_at"),
        "started_by": data.get("started_by"),
        "started_at": data.get("started_at"),
        "completed_by": data.get("completed_by"),
        "completed_at": data.get("completed_at"),
        "completion_evidence": data.get("completion_evidence"),
        "cancelled_by": data.get("cancelled_by"),
        "cancelled_at": data.get("cancelled_at"),
        "cancellation_reason": data.get("cancellation_reason"),
        "record_source": data.get("record_source", "operational"),
        "import_batch_id": data.get("import_batch_id"),
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
        active_order_index = next(
            item for item in WORK_ORDER_INDEXES if item["name"] == "unique_inspection_work_order"
        )
        existing_indexes = await collection.index_information()
        existing_order_index = existing_indexes.get("unique_inspection_work_order")
        if (
            existing_order_index is not None
            and existing_order_index.get("partialFilterExpression")
            != active_order_index["partialFilterExpression"]
        ):
            await collection.drop_index("unique_inspection_work_order")
        await collection.create_index([("vehicle_id", ASCENDING)], name="maintenance_vehicle_id")
        await collection.create_index([("part_id", ASCENDING)], name="maintenance_part_id")
        await collection.create_index([("status", ASCENDING)], name="maintenance_status")
        await collection.create_index([("priority", ASCENDING)], name="maintenance_priority")
        await collection.create_index([("maintenance_type", ASCENDING)], name="maintenance_type")
        await collection.create_index([("maintenance_system", ASCENDING)], name="maintenance_system")
        await collection.create_index([("event_kind", ASCENDING)], name="maintenance_event_kind")
        await collection.create_index([("prediction_review_id", ASCENDING)], name="maintenance_prediction_review_id")
        await collection.create_index([("service_date", DESCENDING)], name="maintenance_service_date")
        for specification in WORK_ORDER_INDEXES:
            options = {key: value for key, value in specification.items() if key != "keys"}
            await collection.create_index(specification["keys"], **options)
    except PyMongoError:
        return
