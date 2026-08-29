from datetime import datetime
from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document
from app.utils.route_utils import DELIVERY_PRIORITIES, DELIVERY_STATUSES, generate_order_code, normalize_priority
from app.utils.branch_operations import apply_branch_origin, build_delivery_schedule, delivery_batch_key
from app.utils.load_profiles import prepare_parcel_load_profile


DELIVERY_COLLECTION = "delivery_orders"


def build_delivery_order_document(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    prepared = apply_branch_origin(data)
    batch_key = delivery_batch_key(prepared)
    if batch_key is None:
        batch_key = delivery_batch_key({"scheduled_date": prepared.get("scheduled_date") or now})
    if batch_key is None:
        raise ValueError("Delivery date and period are required")
    delivery_date, delivery_period = batch_key
    prepared.update(build_delivery_schedule(datetime.fromisoformat(delivery_date).date(), delivery_period))
    load_profile = prepare_parcel_load_profile(prepared, delivery_period=delivery_period)
    return {
        "order_code": prepared.get("order_code") or generate_order_code(),
        "customer_name": prepared.get("customer_name"),
        "customer_phone": prepared.get("customer_phone"),
        "pickup_latitude": float(prepared["pickup_latitude"]),
        "pickup_longitude": float(prepared["pickup_longitude"]),
        "drop_latitude": float(prepared["drop_latitude"]),
        "drop_longitude": float(prepared["drop_longitude"]),
        "pickup_address": prepared.get("pickup_address"),
        "pickup_source": prepared.get("pickup_source"),
        "drop_address": prepared.get("drop_address"),
        "zone_id": prepared.get("zone_id"),
        "operational_zone_id": prepared.get("operational_zone_id"),
        "source_zone_id": prepared.get("source_zone_id"),
        "zone_assignment_method": prepared.get("zone_assignment_method", "nearest"),
        "zone_distance_km": prepared.get("zone_distance_km"),
        "within_service_area": prepared.get("within_service_area", True),
        "is_demo": bool(prepared.get("is_demo", False)),
        "parcel_weight": prepared.get("parcel_weight"),
        "parcel_volume": load_profile.get("volume_m3") or prepared.get("parcel_volume"),
        "load_profile": load_profile,
        "load_planning_status": "unplanned",
        "active_consolidation_id": None,
        "active_load_plan_id": None,
        "active_load_id": None,
        "load_reservation_job_id": None,
        "priority": normalize_priority(prepared.get("priority")),
        "delivery_status": prepared.get("delivery_status", "pending"),
        "cancelled_at": None,
        "cancelled_by": None,
        "cancellation_reason": None,
        "assigned_vehicle_id": prepared.get("assigned_vehicle_id"),
        "assigned_driver_id": prepared.get("assigned_driver_id"),
        "delivery_date": prepared["delivery_date"],
        "delivery_period": prepared["delivery_period"],
        "delivery_window_start": prepared["delivery_window_start"],
        "delivery_window_end": prepared["delivery_window_end"],
        "scheduled_date": prepared["scheduled_date"],
        "created_at": now,
        "updated_at": now,
    }


def safe_delivery_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    safe = serialize_mongo_document(document)
    if safe is None:
        return None
    prepared = apply_branch_origin(safe)
    batch_key = delivery_batch_key(prepared)
    if batch_key:
        delivery_date, delivery_period = batch_key
        schedule = build_delivery_schedule(datetime.fromisoformat(delivery_date).date(), delivery_period)
        prepared.setdefault("delivery_date", schedule["delivery_date"])
        prepared.setdefault("delivery_period", schedule["delivery_period"])
        prepared.setdefault("delivery_window_start", schedule["delivery_window_start"])
        prepared.setdefault("delivery_window_end", schedule["delivery_window_end"])
    return prepared


async def ensure_delivery_indexes() -> None:
    db = get_database()
    if db is None:
        return

    try:
        collection = db[DELIVERY_COLLECTION]
        await collection.create_index([("order_code", ASCENDING)], unique=True, name="unique_delivery_order_code")
        await collection.create_index([("delivery_status", ASCENDING)], name="delivery_status")
        await collection.create_index([("zone_id", ASCENDING)], name="delivery_zone")
        await collection.create_index([("priority", ASCENDING)], name="delivery_priority")
        await collection.create_index([("assigned_vehicle_id", ASCENDING)], name="delivery_assigned_vehicle")
        await collection.create_index([("assigned_driver_id", ASCENDING)], name="delivery_assigned_driver")
        await collection.create_index([("delivery_date", ASCENDING), ("delivery_period", ASCENDING)], name="delivery_operational_batch")
        await collection.create_index([("load_planning_status", ASCENDING)], name="delivery_load_planning_status")
        await collection.create_index([("active_consolidation_id", ASCENDING)], name="delivery_active_consolidation")
        await collection.create_index([("created_at", DESCENDING)], name="delivery_created_at")
    except PyMongoError:
        return
