from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document


TRIP_SESSION_COLLECTION = "driver_trip_sessions"
DRIVER_LOCATION_COLLECTION = "driver_locations"
TRIP_EVENT_COLLECTION = "trip_events"

TRIP_STATUSES = {"active", "completed", "cancelled"}
TRIP_EVENT_TYPES = {
    "trip_started",
    "trip_ended",
    "location_update",
    "stop_arrived",
    "stop_delivered",
    "stop_failed",
    "driver_issue",
}


def build_trip_session_document(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "route_id": data["route_id"],
        "route_code": data.get("route_code"),
        "driver_id": data["driver_id"],
        "vehicle_id": data.get("vehicle_id"),
        "status": data.get("status", "active"),
        "started_at": data.get("started_at", now),
        "ended_at": data.get("ended_at"),
        "created_at": now,
        "updated_at": now,
    }


def build_driver_location_document(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "trip_session_id": data["trip_session_id"],
        "route_id": data["route_id"],
        "driver_id": data["driver_id"],
        "vehicle_id": data.get("vehicle_id"),
        "latitude": float(data["latitude"]),
        "longitude": float(data["longitude"]),
        "accuracy_m": data.get("accuracy_m"),
        "heading": data.get("heading"),
        "speed_mps": data.get("speed_mps"),
        "recorded_at": data.get("recorded_at") or now,
        "created_at": now,
    }


def build_trip_event_document(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "trip_session_id": data.get("trip_session_id"),
        "route_id": data["route_id"],
        "driver_id": data["driver_id"],
        "vehicle_id": data.get("vehicle_id"),
        "delivery_order_id": data.get("delivery_order_id"),
        "event_type": data["event_type"],
        "title": data["title"],
        "description": data.get("description"),
        "severity": data.get("severity", "info"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "created_at": data.get("created_at") or now,
    }


def safe_trip_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    return serialize_mongo_document(document)


async def ensure_trip_indexes() -> None:
    db = get_database()
    if db is None:
        return

    try:
        sessions = db[TRIP_SESSION_COLLECTION]
        await sessions.create_index([("driver_id", ASCENDING), ("status", ASCENDING)], name="trip_driver_status")
        await sessions.create_index([("route_id", ASCENDING), ("status", ASCENDING)], name="trip_route_status")
        await sessions.create_index([("started_at", DESCENDING)], name="trip_started_at")

        locations = db[DRIVER_LOCATION_COLLECTION]
        await locations.create_index([("route_id", ASCENDING), ("recorded_at", DESCENDING)], name="location_route_time")
        await locations.create_index([("driver_id", ASCENDING), ("recorded_at", DESCENDING)], name="location_driver_time")
        await locations.create_index([("trip_session_id", ASCENDING), ("recorded_at", DESCENDING)], name="location_trip_time")

        events = db[TRIP_EVENT_COLLECTION]
        await events.create_index([("route_id", ASCENDING), ("created_at", DESCENDING)], name="event_route_time")
        await events.create_index([("driver_id", ASCENDING), ("created_at", DESCENDING)], name="event_driver_time")
        await events.create_index([("trip_session_id", ASCENDING), ("created_at", DESCENDING)], name="event_trip_time")
        await events.create_index([("event_type", ASCENDING)], name="event_type")
    except PyMongoError:
        return
