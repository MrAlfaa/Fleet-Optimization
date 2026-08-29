from __future__ import annotations

from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.driver_execution_model import VEHICLE_TRIP_INSPECTION_COLLECTION
from app.models.inspection_model import INSPECTION_COLLECTION
from app.models.maintenance_model import MAINTENANCE_COLLECTION
from app.models.predictive_model import PREDICTION_COLLECTION
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.services.maintenance_feature_service import build_vehicle_features
from app.utils.object_id import validate_object_id


MIN_COMPLETED_TRIPS = 5
MIN_RECORDED_DISTANCE_KM = 100.0
REQUIRED_PROFILE_FIELDS = (
    "vehicle_code",
    "registration_number",
    "vehicle_category",
    "fuel_type",
    "year",
    "in_service_date",
    "payload_capacity_kg",
)


def _complete(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, (int, float)):
        return value > 0
    return True


def evaluate_assessment_eligibility(
    *,
    vehicle: dict[str, Any],
    commissioning_passed: bool,
    completed_trip_count: int,
    recorded_distance_km: float,
    imported_history_count: int,
    latest_feature_hash: str | None,
    current_prediction_hash: str | None,
) -> dict[str, Any]:
    missing = [field for field in REQUIRED_PROFILE_FIELDS if not _complete(vehicle.get(field))]
    onboarding_type = str(vehicle.get("onboarding_type") or "existing_fleet")
    trips_complete = completed_trip_count >= MIN_COMPLETED_TRIPS
    distance_complete = recorded_distance_km >= MIN_RECORDED_DISTANCE_KM
    imported_complete = imported_history_count > 0
    history_complete = imported_complete if onboarding_type == "existing_fleet" else trips_complete and distance_complete

    requirements = {
        "profile": {"complete": not missing},
        "commissioning_inspection": {"complete": commissioning_passed},
        "completed_trips": {
            "current": completed_trip_count,
            "required": MIN_COMPLETED_TRIPS,
            "complete": trips_complete,
        },
        "recorded_distance_km": {
            "current": round(recorded_distance_km, 2),
            "required": MIN_RECORDED_DISTANCE_KM,
            "complete": distance_complete,
        },
        "imported_history": {"current": imported_history_count, "complete": imported_complete},
        "history_evidence": {"complete": history_complete},
    }
    blocking: list[str] = []
    if missing:
        blocking.append("Complete the required vehicle profile fields")
        state = "profile_incomplete"
    elif not commissioning_passed:
        blocking.append("Complete and approve the commissioning inspection")
        state = "commissioning_required"
    elif not history_complete:
        if onboarding_type == "existing_fleet":
            blocking.append("Import at least one completed historical service record")
        else:
            if not trips_complete:
                blocking.append(f"Complete {max(MIN_COMPLETED_TRIPS - completed_trip_count, 0)} more trip(s)")
            if not distance_complete:
                blocking.append(
                    f"Record {max(MIN_RECORDED_DISTANCE_KM - recorded_distance_km, 0):g} more km"
                )
        state = "building_history"
    else:
        state = "ready_for_assessment"

    eligible = not blocking
    has_new_data = bool(
        eligible
        and latest_feature_hash
        and latest_feature_hash != current_prediction_hash
    )
    if eligible and current_prediction_hash:
        state = "new_assessment_available" if has_new_data else "assessment_current"

    return {
        "vehicle_id": str(vehicle.get("_id") or vehicle.get("id") or ""),
        "onboarding_type": onboarding_type,
        "eligible": eligible,
        "status": state,
        "has_new_data": has_new_data,
        "missing_profile_fields": missing,
        "blocking_reasons": blocking,
        "requirements": requirements,
    }


async def get_assessment_eligibility(vehicle_id: str) -> dict[str, Any]:
    database = get_database()
    if database is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured")
    try:
        vehicle_oid = validate_object_id(vehicle_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle ID") from exc
    vehicle = await database[VEHICLE_COLLECTION].find_one({"_id": vehicle_oid})
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    current_prediction = await database[PREDICTION_COLLECTION].find_one(
        {"vehicle_id": vehicle_oid}, sort=[("created_at", -1)]
    )
    explicit_onboarding = bool(vehicle.get("onboarding_type"))
    commissioning = await database[INSPECTION_COLLECTION].find_one(
        {
            "vehicle_id": vehicle_oid,
            "inspection_type": "commissioning",
            "status": "returned_to_service",
        },
        sort=[("decided_at", -1)],
    )
    # Existing records created before onboarding controls are treated as commissioned.
    commissioning_passed = commissioning is not None or (not explicit_onboarding and current_prediction is not None)
    post_trips = await database[VEHICLE_TRIP_INSPECTION_COLLECTION].find(
        {"vehicle_id": vehicle_oid, "inspection_type": "post_trip"},
        {"trip_distance_km": 1},
    ).to_list(length=5000)
    imported_count = await database[MAINTENANCE_COLLECTION].count_documents(
        {"vehicle_id": vehicle_oid, "status": "completed", "record_source": "imported_history"}
    )
    if not explicit_onboarding and current_prediction is not None:
        imported_count = max(imported_count, 1)

    basic = evaluate_assessment_eligibility(
        vehicle=vehicle,
        commissioning_passed=commissioning_passed,
        completed_trip_count=len(post_trips),
        recorded_distance_km=sum(max(float(row.get("trip_distance_km") or 0), 0) for row in post_trips),
        imported_history_count=imported_count,
        latest_feature_hash=None,
        current_prediction_hash=str((current_prediction or {}).get("feature_hash") or "") or None,
    )
    if not basic["eligible"]:
        return basic

    feature_result = await build_vehicle_features(vehicle_id)
    return evaluate_assessment_eligibility(
        vehicle=vehicle,
        commissioning_passed=commissioning_passed,
        completed_trip_count=len(post_trips),
        recorded_distance_km=sum(max(float(row.get("trip_distance_km") or 0), 0) for row in post_trips),
        imported_history_count=imported_count,
        latest_feature_hash=feature_result.feature_hash,
        current_prediction_hash=str((current_prediction or {}).get("feature_hash") or "") or None,
    )
