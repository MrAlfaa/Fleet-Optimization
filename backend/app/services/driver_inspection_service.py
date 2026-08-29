from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.delivery_model import DELIVERY_COLLECTION
from app.models.driver_execution_model import VEHICLE_TRIP_INSPECTION_COLLECTION
from app.models.route_model import ROUTE_PLAN_COLLECTION
from app.models.trip_model import TRIP_SESSION_COLLECTION
from app.models.user_model import utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.services.alert_service import create_alert
from app.services.ml_model_loader_service import ModelUnavailableError
from app.services.predictive_maintenance_service import recalculate_vehicle_maintenance
from app.utils.object_id import serialize_mongo_document, serialize_object_id, validate_object_id


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db


def _driver_id(current_user: dict[str, Any]) -> ObjectId:
    try:
        return validate_object_id(current_user["id"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid driver user ID") from exc


def inspection_blocking_reasons(data: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if data.get("tire_condition") == "damaged" or data.get("tire_condition_change") == "significant":
        reasons.append("Tire damage requires inspection")
    if data.get("brake_condition") in {"reduced_response", "warning_light"} or data.get("brake_condition_change") == "significant":
        reasons.append("Brake warning requires inspection")
    if data.get("brake_condition") == "critical":
        reasons.append("Brake condition requires inspection")
    if data.get("tire_condition") == "critical":
        reasons.append("Tire condition requires inspection")
    if data.get("powertrain_condition") == "critical":
        reasons.append("Powertrain condition requires inspection")
    if data.get("charging_or_fuel_issue") == "critical":
        reasons.append("Charging or fuel system requires inspection")
    if data.get("charging_condition") in {"not_charging", "port_damaged"} or data.get("charging_problem") == "failed":
        reasons.append("Charging system requires inspection")
    if data.get("vehicle_damage") == "major":
        reasons.append("Major vehicle damage requires inspection")
    if data.get("dashboard_warning") == "red":
        reasons.append("A red dashboard warning is active")
    if data.get("unusual_noise") == "severe":
        reasons.append("Severe unusual noise requires inspection")
    if data.get("unusual_vibration") == "severe":
        reasons.append("Severe vibration requires inspection")
    return reasons


def inspection_model_features(data: dict[str, Any]) -> dict[str, float]:
    """Compatibility helper: driver observations are never raw ML features."""
    return {}


async def _assigned_route(current_user: dict[str, Any], statuses: set[str]) -> dict[str, Any]:
    route = await _db()[ROUTE_PLAN_COLLECTION].find_one(
        {"driver_id": _driver_id(current_user), "status": {"$in": list(statuses)}},
        sort=[("updated_at", -1), ("created_at", -1)],
    )
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No assigned route is available for inspection")
    if route.get("vehicle_id") is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The assigned route has no vehicle")
    return route


async def _vehicle(route: dict[str, Any]) -> dict[str, Any]:
    vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": route["vehicle_id"]})
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned vehicle was not found")
    return vehicle


async def _run_limited_prediction(
    vehicle: dict[str, Any], data: dict[str, Any], current_user: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return await recalculate_vehicle_maintenance(
            serialize_object_id(vehicle["_id"]),
            {"trigger": data.pop("_prediction_trigger")},
            current_user,
        ), None
    except ModelUnavailableError as exc:
        return None, exc.message
    except HTTPException as exc:
        return None, str(exc.detail)
    except Exception as exc:
        return None, f"Prediction could not be completed: {exc}"


async def _create_block_alert(route: dict[str, Any], vehicle: dict[str, Any], reasons: list[str], inspection_type: str) -> None:
    title = f"Vehicle inspection blocked {route.get('route_code') or route['_id']}"
    if await _db()[ALERT_COLLECTION].find_one({"title": title, "status": "active"}):
        return
    await create_alert({
        "alert_type": "maintenance",
        "severity": "critical",
        "title": title,
        "message": (
            f"{inspection_type.replace('_', ' ').title()} for "
            f"{vehicle.get('registration_number') or vehicle.get('vehicle_code')} reported: {'; '.join(reasons)}"
        ),
        "linked_vehicle_id": serialize_object_id(vehicle["_id"]),
        "status": "active",
        "created_by_system": True,
    })


async def submit_pre_trip_inspection(data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    route = await _assigned_route(current_user, {"dispatched"})
    vehicle = await _vehicle(route)
    current_mileage = float(vehicle.get("current_mileage") or 0)
    if float(data["odometer"]) < current_mileage:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Starting odometer cannot be lower than the recorded vehicle mileage ({current_mileage:g})",
        )

    existing = await _db()[VEHICLE_TRIP_INSPECTION_COLLECTION].find_one({
        "route_id": route["_id"], "driver_id": _driver_id(current_user), "inspection_type": "pre_trip"
    })
    if existing:
        return serialize_mongo_document(existing) or {}

    observation_reasons = inspection_blocking_reasons(data)
    reasons = list(observation_reasons)
    now = utc_now()
    document = {
        "route_id": route["_id"],
        "route_code": route.get("route_code"),
        "driver_id": _driver_id(current_user),
        "vehicle_id": vehicle["_id"],
        "inspection_type": "pre_trip",
        "observations": data,
        "data_quality": "structured_driver_observation",
        "blocking_reasons": reasons,
        "observation_blocking_reasons": observation_reasons,
        "observation_safe_to_operate": not observation_reasons,
        "review_hold": False,
        "safe_to_operate": not reasons,
        "prediction_id": None,
        "prediction_risk": None,
        "prediction_error": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await _db()[VEHICLE_TRIP_INSPECTION_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    if float(data["odometer"]) > current_mileage:
        await _db()[VEHICLE_COLLECTION].update_one(
            {"_id": vehicle["_id"]}, {"$set": {"current_mileage": float(data["odometer"]), "updated_at": now}}
        )
    prediction, prediction_error = await _run_limited_prediction(
        vehicle, {"_prediction_trigger": "driver_pre_trip"}, current_user
    )
    prediction_id = prediction.get("id") if prediction else None
    prediction_update = {
        "prediction_id": validate_object_id(prediction_id) if prediction_id else None,
        "prediction_risk": prediction.get("risk_level") if prediction else None,
        "prediction_error": prediction_error,
        "blocking_reasons": observation_reasons,
        "review_hold": bool(prediction and prediction.get("dispatch_hold")),
        "safe_to_operate": not observation_reasons,
        "updated_at": utc_now(),
    }
    await _db()[VEHICLE_TRIP_INSPECTION_COLLECTION].update_one({"_id": document["_id"]}, {"$set": prediction_update})
    document.update(prediction_update)
    if observation_reasons:
        await _db()[VEHICLE_COLLECTION].update_one(
            {"_id": vehicle["_id"]},
            {"$set": {"status": "under_maintenance", "health_status": "critical", "updated_at": now}},
        )
        await _create_block_alert(route, vehicle, observation_reasons, "pre_trip")
    return serialize_mongo_document(document) or {}


async def submit_post_trip_inspection(data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    route = await _assigned_route(current_user, {"in_progress"})
    session = await _db()[TRIP_SESSION_COLLECTION].find_one({"route_id": route["_id"], "status": "active"})
    if session is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Start the trip before submitting the post-trip inspection")
    deliveries = await _db()[DELIVERY_COLLECTION].find(
        {"_id": {"$in": route.get("delivery_order_ids", [])}}
    ).to_list(length=500)
    unfinished = [
        row for row in deliveries
        if row.get("delivery_status") not in {"delivered", "failed", "cancelled", "rescheduled"}
    ]
    if unfinished:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Process all assigned deliveries before ending the trip ({len(unfinished)} remaining)",
        )
    vehicle = await _vehicle(route)
    pre = await require_pre_trip_inspection(route, current_user)
    starting_odometer = float(pre["observations"]["odometer"])
    if float(data["ending_odometer"]) < starting_odometer:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Ending odometer cannot be lower than the starting odometer")

    existing = await _db()[VEHICLE_TRIP_INSPECTION_COLLECTION].find_one({
        "route_id": route["_id"], "driver_id": _driver_id(current_user), "inspection_type": "post_trip"
    })
    if existing:
        return serialize_mongo_document(existing) or {}

    reasons = inspection_blocking_reasons(data)
    now = utc_now()
    document = {
        "route_id": route["_id"],
        "route_code": route.get("route_code"),
        "trip_session_id": session["_id"],
        "driver_id": _driver_id(current_user),
        "vehicle_id": vehicle["_id"],
        "inspection_type": "post_trip",
        "observations": data,
        "data_quality": "structured_driver_observation",
        "blocking_reasons": reasons,
        "safe_to_operate": not reasons,
        "trip_distance_km": round(float(data["ending_odometer"]) - starting_odometer, 2),
        "battery_soc_used": (
            round(float(pre["observations"]["battery_soc"]) - float(data["ending_battery_soc"]), 2)
            if pre["observations"].get("battery_soc") is not None and data.get("ending_battery_soc") is not None else None
        ),
        "prediction_id": None,
        "prediction_risk": None,
        "prediction_error": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await _db()[VEHICLE_TRIP_INSPECTION_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    vehicle_update: dict[str, Any] = {"current_mileage": float(data["ending_odometer"]), "updated_at": now}
    if reasons:
        vehicle_update.update({"status": "under_maintenance", "health_status": "critical"})
        await _create_block_alert(route, vehicle, reasons, "post_trip")
    await _db()[VEHICLE_COLLECTION].update_one({"_id": vehicle["_id"]}, {"$set": vehicle_update})
    prediction, prediction_error = await _run_limited_prediction(
        vehicle, {"_prediction_trigger": "driver_post_trip"}, current_user
    )
    prediction_id = prediction.get("id") if prediction else None
    prediction_update = {
        "prediction_id": validate_object_id(prediction_id) if prediction_id else None,
        "prediction_risk": prediction.get("risk_level") if prediction else None,
        "prediction_error": prediction_error,
        "updated_at": utc_now(),
    }
    await _db()[VEHICLE_TRIP_INSPECTION_COLLECTION].update_one({"_id": document["_id"]}, {"$set": prediction_update})
    document.update(prediction_update)
    return serialize_mongo_document(document) or {}


async def require_pre_trip_inspection(route: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    inspection = await _db()[VEHICLE_TRIP_INSPECTION_COLLECTION].find_one({
        "route_id": route["_id"], "driver_id": _driver_id(current_user), "inspection_type": "pre_trip"
    })
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Complete the pre-trip vehicle inspection before starting delivery")
    observation_safe = inspection.get("observation_safe_to_operate", inspection.get("safe_to_operate", False))
    if not observation_safe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Vehicle inspection blocked this trip: {'; '.join(inspection.get('observation_blocking_reasons') or inspection.get('blocking_reasons') or [])}",
        )
    return inspection


async def require_post_trip_inspection(route: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    inspection = await _db()[VEHICLE_TRIP_INSPECTION_COLLECTION].find_one({
        "route_id": route["_id"], "driver_id": _driver_id(current_user), "inspection_type": "post_trip"
    })
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Complete the post-trip vehicle inspection before ending delivery")
    return inspection


async def get_driver_inspection_status(current_user: dict[str, Any]) -> dict[str, Any]:
    route = await _assigned_route(current_user, {"dispatched", "in_progress"})
    rows = await _db()[VEHICLE_TRIP_INSPECTION_COLLECTION].find({
        "route_id": route["_id"], "driver_id": _driver_id(current_user)
    }).to_list(length=2)
    by_type = {row["inspection_type"]: row for row in rows}
    return {
        "route_id": serialize_object_id(route["_id"]),
        "vehicle_id": serialize_object_id(route["vehicle_id"]),
        "pre_trip": serialize_mongo_document(by_type.get("pre_trip")),
        "post_trip": serialize_mongo_document(by_type.get("post_trip")),
    }
