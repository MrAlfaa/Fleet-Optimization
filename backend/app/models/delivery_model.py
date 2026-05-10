from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document
from app.utils.route_utils import DELIVERY_PRIORITIES, DELIVERY_STATUSES, generate_order_code, normalize_priority


DELIVERY_COLLECTION = "delivery_orders"


def build_delivery_order_document(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "order_code": data.get("order_code") or generate_order_code(),
        "customer_name": data.get("customer_name"),
        "customer_phone": data.get("customer_phone"),
        "pickup_latitude": float(data["pickup_latitude"]),
        "pickup_longitude": float(data["pickup_longitude"]),
        "drop_latitude": float(data["drop_latitude"]),
        "drop_longitude": float(data["drop_longitude"]),
        "pickup_address": data.get("pickup_address"),
        "drop_address": data.get("drop_address"),
        "zone_id": data.get("zone_id"),
        "parcel_weight": data.get("parcel_weight"),
        "parcel_volume": data.get("parcel_volume"),
        "priority": normalize_priority(data.get("priority")),
        "delivery_status": data.get("delivery_status", "pending"),
        "assigned_vehicle_id": data.get("assigned_vehicle_id"),
        "assigned_driver_id": data.get("assigned_driver_id"),
        "scheduled_date": data.get("scheduled_date"),
        "created_at": now,
        "updated_at": now,
    }


def safe_delivery_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    return serialize_mongo_document(document)


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
        await collection.create_index([("created_at", DESCENDING)], name="delivery_created_at")
    except PyMongoError:
        return
