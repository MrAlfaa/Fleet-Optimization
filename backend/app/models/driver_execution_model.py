from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database

DELIVERY_ATTEMPT_COLLECTION = "delivery_attempts"
DRIVER_ISSUE_COLLECTION = "driver_issue_reports"
VEHICLE_TRIP_INSPECTION_COLLECTION = "vehicle_trip_inspections"

async def ensure_driver_execution_indexes() -> None:
    db = get_database()
    if db is None:
        return
    try:
        await db[DELIVERY_ATTEMPT_COLLECTION].create_index([("idempotency_key", ASCENDING)], unique=True, name="unique_delivery_attempt_key")
        await db[DELIVERY_ATTEMPT_COLLECTION].create_index([("delivery_order_id", ASCENDING), ("created_at", DESCENDING)], name="delivery_attempt_order")
        await db[DRIVER_ISSUE_COLLECTION].create_index([("driver_id", ASCENDING), ("created_at", DESCENDING)], name="driver_issue_driver")
        inspections = db[VEHICLE_TRIP_INSPECTION_COLLECTION]
        await inspections.create_index(
            [("route_id", ASCENDING), ("driver_id", ASCENDING), ("inspection_type", ASCENDING)],
            unique=True,
            name="unique_route_driver_inspection_type",
        )
        await inspections.create_index([("vehicle_id", ASCENDING), ("created_at", DESCENDING)], name="inspection_vehicle_time")
    except PyMongoError:
        return
