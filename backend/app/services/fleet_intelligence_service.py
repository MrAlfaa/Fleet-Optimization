from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.delivery_model import DELIVERY_COLLECTION
from app.models.demand_model import DEMAND_ACTIVE_RUN_COLLECTION, DEMAND_ACTIVE_RUN_POINTER_ID
from app.models.predictive_model import PREDICTION_COLLECTION
from app.models.maintenance_intelligence_model import PREDICTION_REVIEW_COLLECTION
from app.models.inspection_model import INSPECTION_COLLECTION
from app.models.route_model import ROUTE_PLAN_COLLECTION, ROUTE_SEGMENT_COLLECTION
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.services.alert_service import create_alert
from app.utils.object_id import serialize_object_id, validate_object_id
from app.utils.sri_lanka_zones import DATA_CONTEXT, enrich_zone_record, source_zone_id


FLEET_RECOMMENDATION_COLLECTION = "fleet_planning_recommendations"
MAINTENANCE_COLLECTION = "maintenance_records"
BLOCKED_VEHICLE_STATUSES = {"under_maintenance", "inactive", "retired"}


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db


def _label(value: str) -> str:
    return value.replace("_", " ")


def classify_vehicle_readiness(
    vehicle: dict[str, Any],
    prediction: dict[str, Any] | None,
    active_review: dict[str, Any] | None = None,
    active_inspection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    operational_status = str(vehicle.get("status") or "unknown")
    health_status = str(vehicle.get("health_status") or "unknown")
    prediction_risk = str(prediction.get("risk_level")) if prediction and prediction.get("risk_level") else None
    review_status = str((active_review or {}).get("status") or (prediction or {}).get("review_status") or "not_required")
    blocking_reasons: list[str] = []
    warnings: list[str] = []

    if operational_status in BLOCKED_VEHICLE_STATUSES:
        blocking_reasons.append(f"Vehicle status is {_label(operational_status)}")
    if health_status == "critical":
        blocking_reasons.append("Vehicle health status is critical")
    legacy_critical_hold = prediction_risk == "critical" and prediction is not None and "dispatch_hold" not in prediction
    if review_status == "confirmed":
        blocking_reasons.append("Engineering issue requires completed maintenance")
    elif review_status == "pending" or (prediction or {}).get("dispatch_hold") is True:
        blocking_reasons.append("Engineering review is pending")
    elif legacy_critical_hold:
        blocking_reasons.append("Latest predictive maintenance risk is critical")

    if active_inspection and active_inspection.get("is_active") is True:
        inspection_status = str(active_inspection.get("status") or "pending")
        inspection_reasons = {
            "pending": "Vehicle inspection is pending",
            "assigned": "Vehicle inspection is assigned and awaiting start",
            "in_progress": "Vehicle inspection is in progress",
            "completed": "Vehicle inspection is awaiting a service decision",
            "decision_pending": "Active vehicle inspection is awaiting a service decision",
        }
        blocking_reasons.append(
            inspection_reasons.get(inspection_status, "Vehicle has an active maintenance inspection")
        )

    if health_status == "warning":
        warnings.append("Vehicle health status requires monitoring")
    if prediction_risk in {"medium", "high"}:
        warnings.append(f"Latest predictive maintenance risk is {prediction_risk}")
    if prediction_risk == "critical" and review_status == "cleared":
        warnings.append("Critical model result was cleared by engineering review")
    if prediction is None:
        warnings.append("No recent predictive maintenance result is available")

    eligible = not blocking_reasons
    readiness_status = "blocked" if not eligible else "warning" if warnings else "ready"
    return {
        "eligible": eligible,
        "readiness_status": readiness_status,
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "prediction_risk": prediction_risk,
        "review_status": review_status,
    }


async def _latest_predictions(vehicle_ids: list[ObjectId]) -> dict[ObjectId, dict[str, Any]]:
    if not vehicle_ids:
        return {}
    cursor = _db()[PREDICTION_COLLECTION].find({"vehicle_id": {"$in": vehicle_ids}}).sort("created_at", -1)
    result: dict[ObjectId, dict[str, Any]] = {}
    async for row in cursor:
        result.setdefault(row["vehicle_id"], row)
    return result


async def _active_reviews(vehicle_ids: list[ObjectId]) -> dict[ObjectId, dict[str, Any]]:
    if not vehicle_ids:
        return {}
    cursor = _db()[PREDICTION_REVIEW_COLLECTION].find({
        "vehicle_id": {"$in": vehicle_ids}, "status": {"$in": ["pending", "confirmed"]}
    }).sort("created_at", -1)
    result: dict[ObjectId, dict[str, Any]] = {}
    async for row in cursor:
        result.setdefault(row["vehicle_id"], row)
    return result


async def _active_inspections(vehicle_ids: list[ObjectId]) -> dict[ObjectId, dict[str, Any]]:
    if not vehicle_ids:
        return {}
    cursor = _db()[INSPECTION_COLLECTION].find({
        "vehicle_id": {"$in": vehicle_ids}, "is_active": True,
    }).sort("created_at", -1)
    result: dict[ObjectId, dict[str, Any]] = {}
    async for row in cursor:
        result.setdefault(row["vehicle_id"], row)
    return result


async def _selected_forecast_date(value: str | None = None, active_run_id: ObjectId | None = None) -> date:
    resolved_run_id = active_run_id or await _active_demand_run_id()
    if resolved_run_id is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No active demand forecast is available for fleet readiness",
        )
    if value:
        try:
            selected = date.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="forecast_date must use YYYY-MM-DD") from exc
        start, end = _date_window(selected)
        available = await _db()[FLEET_RECOMMENDATION_COLLECTION].find_one({
            "model_run_id": resolved_run_id,
            "forecast_date": {"$gte": start, "$lt": end},
        })
        if available is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected date is outside the active forecast window",
            )
        return selected
    first = await _db()[FLEET_RECOMMENDATION_COLLECTION].find_one(
        {"model_run_id": resolved_run_id}, sort=[("forecast_date", 1)]
    )
    forecast_value = first.get("forecast_date") if first else None
    if isinstance(forecast_value, datetime):
        return forecast_value.date()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="The active demand forecast has no planning records",
    )


def _date_window(selected: date) -> tuple[datetime, datetime]:
    start = datetime.combine(selected, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


async def _active_demand_run_id() -> ObjectId | None:
    pointer = await _db()[DEMAND_ACTIVE_RUN_COLLECTION].find_one({"_id": DEMAND_ACTIVE_RUN_POINTER_ID})
    return pointer.get("model_run_id") if pointer else None


async def _recommendations_for_date(
    selected: date,
    active_run_id: ObjectId,
    active_run_metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    start, end = _date_window(selected)
    rows = await _db()[FLEET_RECOMMENDATION_COLLECTION].find(
        {"model_run_id": active_run_id, "forecast_date": {"$gte": start, "$lt": end}}
    ).sort("predicted_demand", -1).to_list(length=500)
    if not rows:
        return []
    from app.services.operational_demand_service import forecast_vs_actual
    comparison = await forecast_vs_actual(
        start_date=selected,
        end_date=selected,
        model_run_id=active_run_id,
        active_run_metadata=active_run_metadata,
    )
    return sorted(comparison["items"], key=lambda row: float(row.get("predicted_demand") or 0), reverse=True)


def _vehicle_readiness_record(
    vehicle: dict[str, Any],
    prediction: dict[str, Any] | None,
    active_review: dict[str, Any] | None = None,
    active_inspection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    classification = classify_vehicle_readiness(vehicle, prediction, active_review, active_inspection)
    return {
        "vehicle_id": serialize_object_id(vehicle["_id"]),
        "registration_number": vehicle.get("registration_number") or vehicle.get("vehicle_code") or "Unknown",
        "vehicle_code": vehicle.get("vehicle_code") or "Unknown",
        "vehicle_type": vehicle.get("vehicle_type") or "other",
        "vehicle_category": vehicle.get("vehicle_category") or vehicle.get("vehicle_type") or "other",
        "fuel_type": vehicle.get("fuel_type") or "electric",
        "payload_capacity_kg": vehicle.get("payload_capacity_kg"),
        "operational_status": vehicle.get("status") or "unknown",
        "health_status": vehicle.get("health_status") or "unknown",
        **classification,
    }


def _recommendation_item(item_type: str, severity: str, message: str) -> dict[str, str]:
    return {"type": item_type, "severity": severity, "message": message}


async def get_fleet_readiness(forecast_date: str | None = None) -> dict[str, Any]:
    active_run_id, active_run = await _active_forecast_context()
    selected = await _selected_forecast_date(forecast_date, active_run_id)
    demand_rows = await _recommendations_for_date(selected, active_run_id, active_run)
    vehicles = await _db()[VEHICLE_COLLECTION].find({}).sort("registration_number", 1).to_list(length=1000)
    predictions = await _latest_predictions([vehicle["_id"] for vehicle in vehicles])
    active_reviews = await _active_reviews([vehicle["_id"] for vehicle in vehicles])
    active_inspections = await _active_inspections([vehicle["_id"] for vehicle in vehicles])
    readiness = [
        _vehicle_readiness_record(
            vehicle,
            predictions.get(vehicle["_id"]),
            active_reviews.get(vehicle["_id"]),
            active_inspections.get(vehicle["_id"]),
        )
        for vehicle in vehicles
    ]

    eligible = [row for row in readiness if row["eligible"]]
    warning = [row for row in eligible if row["readiness_status"] == "warning"]
    blocked = [row for row in readiness if not row["eligible"]]
    required_vehicles = sum(int(row.get("estimated_required_vehicles") or 0) for row in demand_rows)
    capacity_gap = max(required_vehicles - len(eligible), 0)
    high_zones = [row for row in demand_rows if row.get("demand_level") in {"high", "very_high"}]
    maintenance_count = sum(1 for row in readiness if row["operational_status"] == "under_maintenance")

    recommendations: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    if capacity_gap:
        item = _recommendation_item(
            "capacity_shortage",
            "critical" if capacity_gap >= 3 else "high",
            f"Fleet capacity is short by {capacity_gap} vehicle(s) for {selected.isoformat() if selected else 'the selected forecast period'}.",
        )
        recommendations.append(item)
        conflicts.append(item)
    if blocked:
        recommendations.append(_recommendation_item(
            "maintenance_priority",
            "critical",
            f"{len(blocked)} vehicle(s) are blocked from dispatch; complete inspection or maintenance before assignment.",
        ))
    if high_zones:
        zone_names = ", ".join(row["zone_display_name"] for row in high_zones[:3])
        recommendations.append(_recommendation_item(
            "high_demand_zones",
            "high",
            f"Prioritize fleet allocation for {zone_names}.",
        ))

    active_routes = await _db()[ROUTE_PLAN_COLLECTION].find(
        {"status": {"$in": ["dispatched", "in_progress"]}, "vehicle_id": {"$in": [vehicle["_id"] for vehicle in vehicles]}}
    ).to_list(length=500)
    blocked_ids = {ObjectId(row["vehicle_id"]) for row in blocked}
    risky_routes = [route for route in active_routes if route.get("vehicle_id") in blocked_ids]
    if risky_routes:
        item = _recommendation_item(
            "critical_route_assignment",
            "critical",
            f"{len(risky_routes)} active or dispatched route(s) use vehicles that are now blocked.",
        )
        recommendations.append(item)
        conflicts.append(item)

    return {
        "forecast_date": selected.isoformat() if selected else None,
        "required_vehicles": required_vehicles,
        "eligible_vehicles": len(eligible),
        "warning_vehicles": len(warning),
        "blocked_vehicles": len(blocked),
        "maintenance_vehicles": maintenance_count,
        "capacity_gap": capacity_gap,
        "high_demand_zones": high_zones,
        "vehicle_readiness": readiness,
        "operational_conflicts": conflicts,
        "recommendations": recommendations,
        "data_context": DATA_CONTEXT,
        "active_run": active_run,
    }


async def comparison_metadata() -> dict[str, Any]:
    from app.services.demand_forecasting_service import _active_run_metadata
    return {"active_run": await _active_run_metadata()}


async def _active_forecast_context() -> tuple[ObjectId, dict[str, Any]]:
    from app.services.demand_forecasting_service import _active_run_document, _run_metadata

    run = await _active_run_document()
    if run is None or not isinstance(run.get("_id"), ObjectId):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No active demand forecast is available for fleet readiness",
        )
    return run["_id"], _run_metadata(run)


async def get_fleet_recommendations(days: int = 7) -> dict[str, Any]:
    days = min(max(days, 1), 30)
    readiness = await get_fleet_readiness()
    selected = date.fromisoformat(readiness["forecast_date"]) if readiness.get("forecast_date") else None
    start, _ = _date_window(selected)
    end = start + timedelta(days=days)
    active_run_id = validate_object_id(readiness["active_run"]["model_run_id"])
    rows = await _db()[FLEET_RECOMMENDATION_COLLECTION].find(
        {"model_run_id": active_run_id, "forecast_date": {"$gte": start, "$lt": end}}
    ).sort([("forecast_date", 1), ("predicted_demand", -1)]).to_list(length=2000)
    return {
        "days": days,
        "items": readiness["recommendations"],
        "zones": [enrich_zone_record(row) for row in rows],
        "data_context": DATA_CONTEXT,
        "active_run": readiness.get("active_run"),
    }


async def _create_blocked_assignment_alert(result: dict[str, Any]) -> None:
    title = f"Blocked vehicle assignment for {result['route_code']} - {result['vehicle_registration']}"
    existing = await _db()[ALERT_COLLECTION].find_one({"title": title, "status": "active"})
    if existing:
        return
    await create_alert({
        "alert_type": "route",
        "severity": "critical",
        "title": title,
        "message": "; ".join(result["blocking_reasons"]),
        "linked_vehicle_id": result["vehicle_id"],
        "created_by_system": True,
    })


async def validate_vehicle_assignment(vehicle_id: str, route_id: str, create_block_alert: bool = False) -> dict[str, Any]:
    try:
        vehicle_object_id = validate_object_id(vehicle_id)
        route_object_id = validate_object_id(route_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle or route ID") from exc

    vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": vehicle_object_id})
    route = await _db()[ROUTE_PLAN_COLLECTION].find_one({"_id": route_object_id})
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    prediction = await _db()[PREDICTION_COLLECTION].find_one({"vehicle_id": vehicle_object_id}, sort=[("created_at", -1)])
    active_review = await _db()[PREDICTION_REVIEW_COLLECTION].find_one(
        {"vehicle_id": vehicle_object_id, "status": {"$in": ["pending", "confirmed"]}},
        sort=[("created_at", -1)],
    )
    active_inspection = await _db()[INSPECTION_COLLECTION].find_one({
        "vehicle_id": vehicle_object_id,
        "is_active": True,
    })
    classification = classify_vehicle_readiness(vehicle, prediction, active_review, active_inspection)
    blocking_reasons = list(classification["blocking_reasons"])
    warnings = list(classification["warnings"])
    blocking_maintenance = await _db()[MAINTENANCE_COLLECTION].find_one({
        "vehicle_id": vehicle_object_id,
        "$or": [
            {"status": "in_progress"},
            {"status": "scheduled", "priority": "critical"},
        ],
    })
    if blocking_maintenance:
        blocking_reasons.append(
            f"Open {blocking_maintenance.get('priority', 'critical')} maintenance is {blocking_maintenance.get('status', 'scheduled')}"
        )
    conflicting_route = await _db()[ROUTE_PLAN_COLLECTION].find_one({
        "_id": {"$ne": route_object_id},
        "vehicle_id": vehicle_object_id,
        "status": {"$in": ["dispatched", "in_progress"]},
    })
    if conflicting_route:
        blocking_reasons.append(f"Vehicle is already assigned to active route {conflicting_route.get('route_code', 'Unknown')}")
    average_delay = float(route.get("average_delay_probability") or 0)
    if average_delay >= 0.70:
        warnings.append("Assigned route has high predicted delay risk")
    elif average_delay >= 0.40:
        warnings.append("Assigned route has medium predicted delay risk")

    result = {
        "vehicle_id": vehicle_id,
        "route_id": route_id,
        "vehicle_registration": vehicle.get("registration_number") or vehicle.get("vehicle_code") or "Unknown",
        "vehicle_code": vehicle.get("vehicle_code") or "Unknown",
        "vehicle_type": vehicle.get("vehicle_type") or "other",
        "vehicle_category": vehicle.get("vehicle_category") or vehicle.get("vehicle_type") or "other",
        "fuel_type": vehicle.get("fuel_type") or "electric",
        "payload_capacity_kg": vehicle.get("payload_capacity_kg"),
        "route_code": route.get("route_code") or "Route",
        "eligible": not blocking_reasons,
        "readiness_status": "blocked" if blocking_reasons else classification["readiness_status"],
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "maintenance_risk": classification["prediction_risk"] or vehicle.get("health_status") or "unknown",
        "review_status": classification["review_status"],
        "route_delay_probability": average_delay,
        "demand_context": route.get("demand_context") or {},
    }
    if create_block_alert and not result["eligible"]:
        await _create_blocked_assignment_alert(result)
    return result


async def validate_vehicle_for_planning(vehicle_id: str) -> dict[str, Any]:
    try:
        vehicle_object_id = validate_object_id(vehicle_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle ID") from exc
    vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": vehicle_object_id})
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    prediction = await _db()[PREDICTION_COLLECTION].find_one({"vehicle_id": vehicle_object_id}, sort=[("created_at", -1)])
    review = await _db()[PREDICTION_REVIEW_COLLECTION].find_one(
        {"vehicle_id": vehicle_object_id, "status": {"$in": ["pending", "confirmed"]}},
        sort=[("created_at", -1)],
    )
    inspection = await _db()[INSPECTION_COLLECTION].find_one({"vehicle_id": vehicle_object_id, "is_active": True})
    classification = classify_vehicle_readiness(vehicle, prediction, review, inspection)
    blocking_reasons = list(classification["blocking_reasons"])
    maintenance = await _db()[MAINTENANCE_COLLECTION].find_one({
        "vehicle_id": vehicle_object_id,
        "$or": [{"status": "in_progress"}, {"status": "scheduled", "priority": "critical"}],
    })
    if maintenance:
        blocking_reasons.append("Open critical or in-progress maintenance blocks route planning")
    active_route = await _db()[ROUTE_PLAN_COLLECTION].find_one({
        "vehicle_id": vehicle_object_id,
        "status": {"$in": ["dispatched", "in_progress"]},
    })
    if active_route:
        blocking_reasons.append(f"Vehicle is already assigned to active route {active_route.get('route_code', 'Unknown')}")
    return {
        "eligible": not blocking_reasons,
        "blocking_reasons": blocking_reasons,
        "warnings": list(classification["warnings"]),
        "vehicle": vehicle,
    }


async def get_driver_trip_readiness(current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        driver_id = validate_object_id(current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid driver user ID") from exc
    route = await _db()[ROUTE_PLAN_COLLECTION].find_one(
        {"driver_id": driver_id, "status": {"$in": ["dispatched", "in_progress"]}},
        sort=[("dispatched_at", -1), ("updated_at", -1)],
    )
    if route is None or route.get("vehicle_id") is None:
        return {
            "can_start": False,
            "vehicle_registration": None,
            "vehicle_category": None,
            "fuel_type": None,
            "vehicle_status": "unassigned",
            "maintenance_risk": "unknown",
            "route_delay_risk": "unknown",
            "demand_levels": [],
            "route_distance_km": 0,
            "warnings": ["No dispatched route and vehicle are assigned to this driver"],
            "blocking_reasons": ["No dispatched route and vehicle are assigned"],
        }

    validation = await validate_vehicle_assignment(str(route["vehicle_id"]), str(route["_id"]))
    segments = await _db()[ROUTE_SEGMENT_COLLECTION].find({"route_plan_id": route["_id"]}).to_list(length=500)
    distance = round(sum(float(segment.get("distance_km") or 0) for segment in segments), 2)
    order_ids = route.get("delivery_order_ids") or []
    orders = await _db()[DELIVERY_COLLECTION].find({"_id": {"$in": order_ids}}).to_list(length=500) if order_ids else []
    source_zones = list({source_zone_id(str(order.get("zone_id"))) for order in orders if order.get("zone_id")})
    demand_levels: list[str] = []
    if source_zones:
        active_run_id = await _active_demand_run_id()
        if active_run_id is not None:
            demand_rows = await _db()[FLEET_RECOMMENDATION_COLLECTION].find(
                {"model_run_id": active_run_id, "zone_id": {"$in": source_zones}}
            ).sort("forecast_date", -1).to_list(length=100)
            demand_levels = sorted({str(row.get("demand_level")) for row in demand_rows if row.get("demand_level")})
    warnings = list(validation["warnings"])
    weather_context = route.get("weather_context") or {}
    warnings.extend(str(item) for item in weather_context.get("warnings", []) if item)
    if "very_high" in demand_levels:
        warnings.append("Very high parcel demand is expected on this route")
    elif "high" in demand_levels:
        warnings.append("High parcel demand is expected on this route")

    delay_probability = validation["route_delay_probability"]
    delay_risk = "high" if delay_probability >= 0.70 else "medium" if delay_probability >= 0.40 else "low"
    return {
        "can_start": validation["eligible"],
        "vehicle_registration": validation["vehicle_registration"],
        "vehicle_category": validation["vehicle_category"],
        "fuel_type": validation["fuel_type"],
        "vehicle_status": validation["readiness_status"],
        "maintenance_risk": validation["maintenance_risk"],
        "review_status": validation["review_status"],
        "route_delay_risk": delay_risk,
        "demand_levels": demand_levels,
        "route_distance_km": distance,
        "warnings": warnings,
        "blocking_reasons": validation["blocking_reasons"],
        "route_id": str(route["_id"]),
        "route_code": route.get("route_code"),
        "weather_context": weather_context,
    }
