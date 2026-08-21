from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.delivery_model import DELIVERY_COLLECTION
from app.models.driver_execution_model import DELIVERY_ATTEMPT_COLLECTION, DRIVER_ISSUE_COLLECTION
from app.models.route_model import ROUTE_PLAN_COLLECTION, ROUTE_SEGMENT_COLLECTION
from app.models.user_model import utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.services.alert_service import create_alert, resolve_alert
from app.services.delivery_service import update_delivery_status
from app.services.live_trip_service import create_delivery_status_trip_event, create_driver_issue_trip_event
from app.utils.object_id import serialize_mongo_document, serialize_mongo_list, serialize_object_id, validate_object_id
from app.utils.sri_lanka_zones import enrich_zone_record


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


def calculate_next_delivery_schedule(scheduled: datetime | None, now: datetime | None = None) -> datetime:
    colombo = ZoneInfo("Asia/Colombo")
    if isinstance(scheduled, datetime):
        source = scheduled.replace(tzinfo=ZoneInfo("UTC")) if scheduled.tzinfo is None else scheduled
        local = source.astimezone(colombo) + timedelta(days=1)
    else:
        local_now = (now or datetime.now(colombo)).astimezone(colombo)
        local = (local_now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    return local.astimezone(ZoneInfo("UTC"))


async def get_assigned_route_raw(current_user: dict[str, Any]) -> dict[str, Any] | None:
    driver_id = _driver_object_id(current_user)
    return await _db()[ROUTE_PLAN_COLLECTION].find_one(
        {"driver_id": driver_id, "status": {"$in": ["dispatched", "in_progress"]}},
        sort=[("dispatched_at", -1), ("updated_at", -1), ("created_at", -1)],
    )


async def get_assigned_vehicle(current_user: dict[str, Any]) -> dict[str, Any] | None:
    route = await get_assigned_route_raw(current_user)
    vehicle_id = route.get("vehicle_id") if route else None
    if vehicle_id is None:
        vehicle = await _db()[VEHICLE_COLLECTION].find_one({"assigned_driver_id": _driver_object_id(current_user)})
    else:
        vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": vehicle_id})

    if vehicle is None:
        return None

    return {
        "id": serialize_object_id(vehicle["_id"]),
        "vehicle_code": vehicle.get("vehicle_code"),
        "registration_number": vehicle.get("registration_number"),
        "vehicle_type": vehicle.get("vehicle_type"),
        "brand": vehicle.get("brand"),
        "model": vehicle.get("model"),
        "current_mileage": vehicle.get("current_mileage", 0),
        "health_status": vehicle.get("health_status", "unknown"),
        "status": vehicle.get("status"),
        "risk_summary": _vehicle_risk_summary(vehicle.get("health_status", "unknown")),
        "model_status": "Predictive maintenance backend connected",
    }


def _vehicle_risk_summary(health_status: str) -> str:
    if health_status == "critical":
        return "Critical maintenance risk detected. Contact fleet manager before continuing route."
    if health_status == "warning":
        return "Vehicle has warning maintenance status. Monitor closely and report abnormal behavior."
    if health_status == "healthy":
        return "Vehicle is currently marked healthy for route assignment."
    return "No recent predictive maintenance result is available for this vehicle."


async def _route_delivery_rows(route: dict[str, Any]) -> list[dict[str, Any]]:
    order_ids = route.get("delivery_order_ids", [])
    if not order_ids:
        return []
    rows = await _db()[DELIVERY_COLLECTION].find({"_id": {"$in": order_ids}}).to_list(length=200)
    by_id = {row["_id"]: row for row in rows}
    return [by_id[order_id] for order_id in order_ids if order_id in by_id]


def _eta_for_stop(route: dict[str, Any], sequence: int) -> str:
    stops_count = max(len(route.get("delivery_order_ids", [])), 1)
    total_eta = float(route.get("total_predicted_eta_minutes") or 0)
    if total_eta <= 0:
        return "--"
    return f"{round((total_eta / stops_count) * sequence)} min"


def _mobile_stop(row: dict[str, Any], sequence: int, route: dict[str, Any]) -> dict[str, Any]:
    zone = enrich_zone_record({"zone_id": row.get("zone_id")}) if row.get("zone_id") else None
    return {
        "id": serialize_object_id(row["_id"]),
        "sequence": sequence,
        "customer_name": row.get("customer_name") or row.get("order_code") or f"Stop {sequence}",
        "drop_address": row.get("drop_address") or f"{row.get('drop_latitude', 0)}, {row.get('drop_longitude', 0)}",
        "zone_id": zone["zone_display_name"] if zone else "Unassigned zone",
        "operational_zone_id": zone["operational_zone_id"] if zone else None,
        "eta": _eta_for_stop(route, sequence),
        "priority": row.get("priority", "medium"),
        "drop_latitude": float(row.get("drop_latitude") or 0),
        "drop_longitude": float(row.get("drop_longitude") or 0),
        "delivery_status": row.get("delivery_status", "pending"),
    }


async def get_assigned_route(current_user: dict[str, Any]) -> dict[str, Any]:
    route = await get_assigned_route_raw(current_user)
    if route is None:
        return {"route": None, "stops": []}

    delivery_rows = await _route_delivery_rows(route)
    segments = await _db()[ROUTE_SEGMENT_COLLECTION].find({"route_plan_id": route["_id"]}).to_list(length=200)
    total_distance_km = sum(float(segment.get("distance_km") or 0) for segment in segments)
    stops = [_mobile_stop(row, index + 1, route) for index, row in enumerate(delivery_rows)]
    next_stop = next(
        (stop for stop in stops if stop["delivery_status"] not in {"delivered", "failed", "cancelled", "rescheduled"}),
        None,
    )
    return {
        "route": {
            "id": serialize_object_id(route["_id"]),
            "route_code": route.get("route_code"),
            "route_name": route.get("route_name") or route.get("route_code"),
            "depot_name": route.get("depot_name") or "Depot",
            "depot_latitude": route.get("depot_latitude"),
            "depot_longitude": route.get("depot_longitude"),
            "total_distance_km": total_distance_km,
            "total_predicted_eta_minutes": float(route.get("total_predicted_eta_minutes") or 0),
            "total_route_cost_score": float(route.get("total_route_cost_score") or 0),
            "average_delay_probability": float(route.get("average_delay_probability") or 0),
            "status": route.get("status"),
            "dispatched_at": _iso_or_none(route.get("dispatched_at")),
        },
        "stops": stops,
        "next_stop": next_stop,
    }


async def get_driver_alerts(current_user: dict[str, Any]) -> list[dict[str, Any]]:
    route = await get_assigned_route_raw(current_user)
    vehicle_id = route.get("vehicle_id") if route else None
    route_code = route.get("route_code") if route else None

    filters: list[dict[str, Any]] = [{"alert_type": "system", "status": "active"}]
    if vehicle_id:
        filters.append({"linked_vehicle_id": vehicle_id})
    if route_code:
        filters.append({"alert_type": "route", "title": {"$regex": route_code, "$options": "i"}})

    cursor = _db()[ALERT_COLLECTION].find({"$or": filters}).sort("created_at", -1).limit(50)
    return serialize_mongo_list(await cursor.to_list(length=50))


async def update_driver_delivery_status(order_id: str, status_value: str, current_user: dict[str, Any]) -> dict[str, Any]:
    driver_id = _driver_object_id(current_user)
    route = await get_assigned_route_raw(current_user)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active route assigned to this driver")
    try:
        object_id = validate_object_id(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid delivery order ID") from exc

    delivery = await _db()[DELIVERY_COLLECTION].find_one({"_id": object_id})
    if delivery is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery order not found")
    if delivery.get("assigned_driver_id") != driver_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Delivery order is not assigned to this driver")
    if object_id not in route.get("delivery_order_ids", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Delivery order is not part of this driver's active route")

    updated = await update_delivery_status(order_id, status_value)
    await create_delivery_status_trip_event(order_id, status_value, route, delivery)
    return updated


async def mark_driver_delivery_incomplete(order_id: str, data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    driver_id = _driver_object_id(current_user)
    route = await get_assigned_route_raw(current_user)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active route assigned to this driver")
    order_object_id = validate_object_id(order_id)
    delivery = await _db()[DELIVERY_COLLECTION].find_one({"_id": order_object_id})
    if delivery is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery order not found")
    if delivery.get("assigned_driver_id") != driver_id or order_object_id not in route.get("delivery_order_ids", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Delivery order is not assigned to this driver's active route")

    existing = await _db()[DELIVERY_ATTEMPT_COLLECTION].find_one({"idempotency_key": data["idempotency_key"]})
    if existing:
        return {"delivery": serialize_mongo_document(await _db()[DELIVERY_COLLECTION].find_one({"_id": existing["delivery_order_id"]})), "attempt": serialize_mongo_document(existing)}

    scheduled = delivery.get("scheduled_date")
    next_date = calculate_next_delivery_schedule(scheduled)
    local = next_date.astimezone(ZoneInfo("Asia/Colombo"))
    now = utc_now()
    attempt = {
        "delivery_order_id": order_object_id,
        "route_id": route["_id"],
        "driver_id": driver_id,
        "vehicle_id": route.get("vehicle_id"),
        "result": "incomplete",
        "reason": data["reason"],
        "details": data.get("details"),
        "previous_scheduled_date": scheduled,
        "next_scheduled_date": next_date,
        "idempotency_key": data["idempotency_key"],
        "created_at": now,
    }
    try:
        result = await _db()[DELIVERY_ATTEMPT_COLLECTION].insert_one(attempt)
    except DuplicateKeyError:
        existing = await _db()[DELIVERY_ATTEMPT_COLLECTION].find_one({"idempotency_key": data["idempotency_key"]})
        return {"delivery": serialize_mongo_document(await _db()[DELIVERY_COLLECTION].find_one({"_id": existing["delivery_order_id"]})), "attempt": serialize_mongo_document(existing)}
    attempt["_id"] = result.inserted_id
    await _db()[DELIVERY_COLLECTION].update_one(
        {"_id": order_object_id},
        {"$set": {"delivery_status": "rescheduled", "scheduled_date": next_date, "last_failure_reason": data["reason"], "last_failure_details": data.get("details"), "updated_at": now}, "$unset": {"assigned_driver_id": "", "assigned_vehicle_id": ""}},
    )
    await create_delivery_status_trip_event(order_id, "failed", route, delivery)
    await create_alert({
        "alert_type": "route", "severity": "warning",
        "title": f"Delivery {delivery.get('order_code') or order_id} rescheduled",
        "message": f"{data['reason'].replace('_', ' ')}. Next attempt: {local.strftime('%Y-%m-%d %H:%M')}",
        "status": "active", "created_by_system": True,
    })
    return {"delivery": serialize_mongo_document(await _db()[DELIVERY_COLLECTION].find_one({"_id": order_object_id})), "attempt": serialize_mongo_document(attempt)}


async def get_delivery_attempts_for_driver(order_id: str, current_user: dict[str, Any]) -> list[dict[str, Any]]:
    driver_id = _driver_object_id(current_user)
    order_object_id = validate_object_id(order_id)
    delivery = await _db()[DELIVERY_COLLECTION].find_one({"_id": order_object_id})
    if delivery is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery order not found")
    if delivery.get("assigned_driver_id") not in {None, driver_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Delivery order is not available to this driver")
    return serialize_mongo_list(await _db()[DELIVERY_ATTEMPT_COLLECTION].find({"delivery_order_id": order_object_id, "driver_id": driver_id}).sort("created_at", -1).to_list(length=50))


async def create_driver_issue(data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    route = await get_assigned_route_raw(current_user)
    assigned_vehicle_id = serialize_object_id(route.get("vehicle_id")) if route and route.get("vehicle_id") else None
    if assigned_vehicle_id is None:
        assigned_vehicle = await _db()[VEHICLE_COLLECTION].find_one({"assigned_driver_id": _driver_object_id(current_user)})
        assigned_vehicle_id = serialize_object_id(assigned_vehicle["_id"]) if assigned_vehicle else None
    assigned_route_id = serialize_object_id(route["_id"]) if route else None

    requested_vehicle_id = data.get("vehicle_id")
    requested_route_id = data.get("route_id")
    vehicle_id = requested_vehicle_id or assigned_vehicle_id
    route_id = requested_route_id or assigned_route_id

    if requested_vehicle_id and requested_vehicle_id != assigned_vehicle_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Driver can only report issues for the assigned vehicle")
    if requested_route_id and requested_route_id != assigned_route_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Driver can only report issues for the assigned route")

    message = data["message"]
    if route_id:
        message = f"{message}\nRoute ID: {route_id}"
    if current_user.get("email"):
        message = f"{message}\nReported by: {current_user['email']}"

    alert = await create_alert(
        {
            "alert_type": "driver",
            "severity": data.get("severity", "warning"),
            "title": data["title"],
            "message": message,
            "linked_vehicle_id": vehicle_id,
            "status": "active",
            "created_by_system": False,
            "created_at": utc_now(),
        }
    )
    issue = {
        "driver_id": _driver_object_id(current_user),
        "vehicle_id": validate_object_id(vehicle_id) if vehicle_id else None,
        "route_id": validate_object_id(route_id) if route_id else None,
        "stop_id": data.get("stop_id"),
        "category": data.get("category", "other"),
        "severity": data.get("severity", "warning"),
        "title": data["title"],
        "description": data["message"],
        "status": "open",
        "linked_alert_id": validate_object_id(alert["id"]),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    await _db()[DRIVER_ISSUE_COLLECTION].insert_one(issue)
    if route is not None:
        await create_driver_issue_trip_event(route, data["title"], data["message"], data.get("severity", "warning"))
    return alert


async def acknowledge_driver_alert(alert_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    visible_alert_ids = {alert["id"] for alert in await get_driver_alerts(current_user)}
    if alert_id not in visible_alert_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Alert is not visible to this driver")
    return await resolve_alert(alert_id, current_user)
