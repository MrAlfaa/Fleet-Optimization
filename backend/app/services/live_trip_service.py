from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.delivery_model import DELIVERY_COLLECTION
from app.models.route_model import ROUTE_PLAN_COLLECTION
from app.models.trip_model import (
    DRIVER_LOCATION_COLLECTION,
    TRIP_EVENT_COLLECTION,
    TRIP_SESSION_COLLECTION,
    build_driver_location_document,
    build_trip_event_document,
    build_trip_session_document,
    safe_trip_document,
)
from app.models.user_model import USER_COLLECTION, utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.services.fleet_intelligence_service import get_driver_trip_readiness, validate_vehicle_assignment
from app.services.driver_inspection_service import require_post_trip_inspection, require_pre_trip_inspection
from app.utils.object_id import serialize_mongo_list, serialize_object_id, validate_object_id


TERMINAL_DELIVERY_STATUSES = {"delivered", "failed", "cancelled", "rescheduled"}


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db


def _driver_object_id(current_user: dict[str, Any]) -> ObjectId:
    try:
        return validate_object_id(current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid driver user ID") from exc


def _iso_or_none(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return None
    return str(value)


async def get_assigned_trip_route(current_user: dict[str, Any]) -> dict[str, Any] | None:
    driver_id = _driver_object_id(current_user)
    return await _db()[ROUTE_PLAN_COLLECTION].find_one(
        {"driver_id": driver_id, "status": {"$in": ["dispatched", "in_progress"]}},
        sort=[("dispatched_at", -1), ("updated_at", -1), ("created_at", -1)],
    )


async def _active_session_for_route(route: dict[str, Any]) -> dict[str, Any] | None:
    return await _db()[TRIP_SESSION_COLLECTION].find_one({"route_id": route["_id"], "status": "active"})


async def create_trip_event(data: dict[str, Any]) -> dict[str, Any]:
    document = build_trip_event_document(data)
    result = await _db()[TRIP_EVENT_COLLECTION].insert_one(document)
    return safe_trip_document(await _db()[TRIP_EVENT_COLLECTION].find_one({"_id": result.inserted_id}))


async def _create_route_event(
    route: dict[str, Any],
    event_type: str,
    title: str,
    description: str | None = None,
    severity: str = "info",
    delivery_order_id: ObjectId | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    session = await _active_session_for_route(route)
    return await create_trip_event(
        {
            "trip_session_id": session["_id"] if session else None,
            "route_id": route["_id"],
            "driver_id": route["driver_id"],
            "vehicle_id": route.get("vehicle_id"),
            "delivery_order_id": delivery_order_id,
            "event_type": event_type,
            "title": title,
            "description": description,
            "severity": severity,
            "latitude": latitude,
            "longitude": longitude,
        }
    )


async def start_driver_trip(current_user: dict[str, Any]) -> dict[str, Any]:
    route = await get_assigned_trip_route(current_user)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No dispatched route assigned to this driver")

    await require_pre_trip_inspection(route, current_user)

    readiness = await get_driver_trip_readiness(current_user)
    if not readiness["can_start"]:
        if route.get("vehicle_id"):
            await validate_vehicle_assignment(str(route["vehicle_id"]), str(route["_id"]), create_block_alert=True)
        reasons = readiness.get("blocking_reasons") or ["Vehicle is not ready for dispatch"]
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Trip cannot start: {'; '.join(reasons)}")

    active_session = await _active_session_for_route(route)
    if active_session is None:
        document = build_trip_session_document(
            {
                "route_id": route["_id"],
                "route_code": route.get("route_code"),
                "driver_id": route["driver_id"],
                "vehicle_id": route.get("vehicle_id"),
            }
        )
        result = await _db()[TRIP_SESSION_COLLECTION].insert_one(document)
        active_session = await _db()[TRIP_SESSION_COLLECTION].find_one({"_id": result.inserted_id})
        await create_trip_event(
            {
                "trip_session_id": active_session["_id"],
                "route_id": route["_id"],
                "driver_id": route["driver_id"],
                "vehicle_id": route.get("vehicle_id"),
                "event_type": "trip_started",
                "title": "Trip started",
                "description": f"{route.get('route_code') or 'Route'} started by driver.",
                "severity": "info",
            }
        )

    await _db()[ROUTE_PLAN_COLLECTION].update_one(
        {"_id": route["_id"]},
        {"$set": {"status": "in_progress", "updated_at": utc_now()}},
    )

    return {
        "trip_session_id": serialize_object_id(active_session["_id"]),
        "route_id": serialize_object_id(route["_id"]),
        "route_code": route.get("route_code"),
        "status": active_session.get("status", "active"),
        "started_at": _iso_or_none(active_session.get("started_at")),
    }


async def end_driver_trip(current_user: dict[str, Any]) -> dict[str, Any]:
    route = await get_assigned_trip_route(current_user)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active route assigned to this driver")
    session = await _active_session_for_route(route)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active trip session found for this route")

    await require_post_trip_inspection(route, current_user)

    now = utc_now()
    await _db()[TRIP_SESSION_COLLECTION].update_one(
        {"_id": session["_id"]},
        {"$set": {"status": "completed", "ended_at": now, "updated_at": now}},
    )
    await create_trip_event(
        {
            "trip_session_id": session["_id"],
            "route_id": route["_id"],
            "driver_id": route["driver_id"],
            "vehicle_id": route.get("vehicle_id"),
            "event_type": "trip_ended",
            "title": "Trip ended",
            "description": f"{route.get('route_code') or 'Route'} ended by driver.",
            "severity": "info",
        }
    )

    deliveries = await _db()[DELIVERY_COLLECTION].find({"_id": {"$in": route.get("delivery_order_ids", [])}}).to_list(length=500)
    all_terminal = bool(deliveries) and all(row.get("delivery_status") in TERMINAL_DELIVERY_STATUSES for row in deliveries)
    route_status = "completed" if all_terminal else route.get("status", "in_progress")
    route_update: dict[str, Any] = {"updated_at": now}
    if all_terminal:
        route_update["status"] = "completed"
        route_update["completed_at"] = now
    await _db()[ROUTE_PLAN_COLLECTION].update_one({"_id": route["_id"]}, {"$set": route_update})

    return {
        "trip_session_id": serialize_object_id(session["_id"]),
        "route_id": serialize_object_id(route["_id"]),
        "route_code": route.get("route_code"),
        "status": "completed",
        "route_status": route_status,
        "ended_at": _iso_or_none(now),
    }


async def record_driver_location(data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    route = await get_assigned_trip_route(current_user)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active route assigned to this driver")
    session = await _active_session_for_route(route)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Start the trip before sending location updates")

    document = build_driver_location_document(
        {
            **data,
            "trip_session_id": session["_id"],
            "route_id": route["_id"],
            "driver_id": route["driver_id"],
            "vehicle_id": route.get("vehicle_id"),
        }
    )
    result = await _db()[DRIVER_LOCATION_COLLECTION].insert_one(document)
    return safe_trip_document(await _db()[DRIVER_LOCATION_COLLECTION].find_one({"_id": result.inserted_id}))


async def create_delivery_status_trip_event(order_id: str, status_value: str, route: dict[str, Any], delivery: dict[str, Any]) -> None:
    event_map = {
        "arrived": ("stop_arrived", "Stop arrived", "Driver arrived at delivery stop.", "info"),
        "delivered": ("stop_delivered", "Stop delivered", "Delivery marked as completed.", "info"),
        "failed": ("stop_failed", "Stop failed", "Delivery could not be completed.", "warning"),
    }
    if status_value not in event_map:
        return
    event_type, title, description, severity = event_map[status_value]
    await _create_route_event(
        route,
        event_type,
        title,
        description=f"{description} Order: {delivery.get('order_code') or order_id}.",
        severity=severity,
        delivery_order_id=delivery["_id"],
        latitude=delivery.get("drop_latitude"),
        longitude=delivery.get("drop_longitude"),
    )


async def create_driver_issue_trip_event(route: dict[str, Any], title: str, message: str, severity: str) -> None:
    await _create_route_event(
        route,
        "driver_issue",
        title,
        description=message,
        severity="critical" if severity == "critical" else "warning",
    )


async def get_driver_trip_events(current_user: dict[str, Any]) -> list[dict[str, Any]]:
    route = await get_assigned_trip_route(current_user)
    if route is None:
        return []
    cursor = _db()[TRIP_EVENT_COLLECTION].find({"route_id": route["_id"]}).sort("created_at", -1).limit(50)
    return serialize_mongo_list(await cursor.to_list(length=50))


async def _latest_location(route_id: ObjectId) -> dict[str, Any] | None:
    document = await _db()[DRIVER_LOCATION_COLLECTION].find_one({"route_id": route_id}, sort=[("recorded_at", -1), ("created_at", -1)])
    return safe_trip_document(document)


async def _latest_event(route_id: ObjectId) -> dict[str, Any] | None:
    document = await _db()[TRIP_EVENT_COLLECTION].find_one({"route_id": route_id}, sort=[("created_at", -1)])
    return safe_trip_document(document)


async def _progress(route: dict[str, Any]) -> dict[str, int]:
    order_ids = route.get("delivery_order_ids", [])
    if not order_ids:
        return {"total_stops": 0, "completed_stops": 0}
    deliveries = await _db()[DELIVERY_COLLECTION].find({"_id": {"$in": order_ids}}).to_list(length=500)
    return {
        "total_stops": len(deliveries),
        "completed_stops": sum(1 for row in deliveries if row.get("delivery_status") == "delivered"),
    }


async def _user_name(user_id: ObjectId | None) -> str:
    if user_id is None:
        return "Unassigned driver"
    user = await _db()[USER_COLLECTION].find_one({"_id": user_id})
    return user.get("full_name") if user else "Unassigned driver"


async def _vehicle_identity(vehicle_id: ObjectId | None) -> dict[str, str]:
    if vehicle_id is None:
        return {"registration_number": "Unassigned vehicle", "vehicle_code": "Unassigned vehicle"}
    vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": vehicle_id})
    if vehicle is None:
        return {"registration_number": "Unassigned vehicle", "vehicle_code": "Unassigned vehicle"}
    return {
        "registration_number": vehicle.get("registration_number") or vehicle.get("vehicle_code") or "Unknown vehicle",
        "vehicle_code": vehicle.get("vehicle_code") or "Unknown vehicle",
    }


async def _live_trip_card(route: dict[str, Any], session: dict[str, Any] | None = None) -> dict[str, Any]:
    session = session or await _active_session_for_route(route)
    vehicle_identity = await _vehicle_identity(route.get("vehicle_id"))
    return {
        "route_id": serialize_object_id(route["_id"]),
        "route_code": route.get("route_code"),
        "route_name": route.get("route_name") or route.get("route_code"),
        "driver_name": await _user_name(route.get("driver_id")),
        "vehicle_registration": vehicle_identity["registration_number"],
        "vehicle_code": vehicle_identity["registration_number"],
        "vehicle_internal_code": vehicle_identity["vehicle_code"],
        "trip_status": session.get("status") if session else "inactive",
        "route_status": route.get("status"),
        "started_at": _iso_or_none(session.get("started_at")) if session else None,
        "ended_at": _iso_or_none(session.get("ended_at")) if session else None,
        "latest_location": await _latest_location(route["_id"]),
        "progress": await _progress(route),
        "latest_event": await _latest_event(route["_id"]),
    }


async def list_live_trips() -> dict[str, Any]:
    active_sessions = await _db()[TRIP_SESSION_COLLECTION].find({"status": "active"}).sort("started_at", -1).to_list(length=200)
    cards: list[dict[str, Any]] = []
    for session in active_sessions:
        route = await _db()[ROUTE_PLAN_COLLECTION].find_one({"_id": session["route_id"]})
        if route:
            cards.append(await _live_trip_card(route, session))
    return {"items": cards, "total": len(cards)}


async def get_live_trip(route_id: str) -> dict[str, Any] | None:
    try:
        object_id = validate_object_id(route_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid route ID") from exc
    route = await _db()[ROUTE_PLAN_COLLECTION].find_one({"_id": object_id})
    if route is None:
        return None
    return await _live_trip_card(route)


async def get_live_trip_locations(route_id: str, limit: int = 100) -> list[dict[str, Any]]:
    try:
        object_id = validate_object_id(route_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid route ID") from exc
    cursor = _db()[DRIVER_LOCATION_COLLECTION].find({"route_id": object_id}).sort("recorded_at", -1).limit(limit)
    return serialize_mongo_list(await cursor.to_list(length=limit))


async def get_live_trip_events(route_id: str, limit: int = 100) -> list[dict[str, Any]]:
    try:
        object_id = validate_object_id(route_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid route ID") from exc
    cursor = _db()[TRIP_EVENT_COLLECTION].find({"route_id": object_id}).sort("created_at", -1).limit(limit)
    return serialize_mongo_list(await cursor.to_list(length=limit))
