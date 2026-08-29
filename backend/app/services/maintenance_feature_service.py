from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.delivery_model import DELIVERY_COLLECTION
from app.models.driver_execution_model import VEHICLE_TRIP_INSPECTION_COLLECTION
from app.models.maintenance_model import MAINTENANCE_COLLECTION
from app.models.route_model import ROUTE_PLAN_COLLECTION
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.services.predictive_artifact_registry import predictive_artifact_registry
from app.utils.object_id import serialize_object_id, validate_object_id


SYSTEMS = (
    "battery_system",
    "braking",
    "charging_system",
    "cooling_system",
    "electrical",
    "engine",
    "exhaust_dpf",
    "fuel_system",
    "ignition",
    "motor_drivetrain",
    "steering",
    "suspension",
    "thermal_system",
    "tires",
)

FEATURE_COLUMNS = [
    "fuel_type", "vehicle_category", "vehicle_age_years", "current_odometer_km",
    "trip_distance_km", "distance_last_7d_km", "distance_last_30d_km",
    "distance_last_90d_km", "trip_count_last_30d", "average_load_ratio_30d",
    "average_route_roughness_30d", "days_since_last_maintenance",
    "km_since_last_maintenance", "maintenance_count_90d", "maintenance_count_365d",
    "unplanned_repair_count_365d", "breakdown_count_365d", "lifetime_unplanned_repairs",
    "days_since_last_unplanned_repair", "km_since_last_unplanned_repair",
    "highest_failure_exposure_system", "highest_failure_exposure_ratio",
    "second_failure_exposure_system", "second_failure_exposure_ratio",
    "third_failure_exposure_system", "third_failure_exposure_ratio",
    "overexposed_system_count", "expected_failure_km_remaining",
    "expected_failure_days_remaining", "most_due_service_system",
    "maximum_service_usage_ratio", "overdue_service_system_count",
    "days_until_next_scheduled_service", "km_until_next_scheduled_service",
    *[f"{system}_failure_exposure_ratio" for system in SYSTEMS],
    "brake_condition", "tire_condition", "powertrain_condition", "warning_light_level",
    "charging_or_fuel_issue", "unusual_noise", "vibration_level", "vehicle_damage",
]

DEFAULT_PAYLOAD_KG = {"car": 450.0, "van": 1_400.0, "truck": 6_500.0, "bus": 8_500.0}
UNPLANNED_EVENT_KINDS = {"corrective_repair", "breakdown"}


@dataclass(frozen=True)
class FeatureBuildResult:
    features: dict[str, Any]
    feature_hash: str
    defaulted_fields: list[str]
    quality_grade: str
    source_ids: dict[str, list[str]]


def _as_utc(value: Any, fallback: datetime) -> datetime:
    if not isinstance(value, datetime):
        return fallback
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _days_between(later: datetime, earlier: datetime) -> float:
    return max((later - earlier).total_seconds() / 86_400, 0.0)


def _event_kind(record: dict[str, Any]) -> str:
    explicit = record.get("event_kind")
    if explicit:
        return str(explicit)
    issue = str(record.get("issue_type") or "").lower()
    if "breakdown" in issue or "failure" in issue:
        return "breakdown"
    maintenance_type = record.get("maintenance_type")
    if maintenance_type == "inspection":
        return "inspection"
    if maintenance_type in {"corrective", "replacement"}:
        return "corrective_repair"
    return "scheduled_service"


def _condition(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"critical", "red", "major", "severe", "damaged", "failed", "not_charging", "port_damaged"}:
        return "critical"
    if normalized in {
        "warning", "amber", "yellow", "minor", "moderate", "significant",
        "reduced_response", "warning_light", "change", "changed",
    }:
        return "warning"
    return "normal"


def _category(vehicle: dict[str, Any]) -> tuple[str, bool]:
    value = str(vehicle.get("vehicle_category") or "").lower()
    if value in DEFAULT_PAYLOAD_KG:
        return value, False
    legacy = str(vehicle.get("vehicle_type") or "").lower()
    for category in DEFAULT_PAYLOAD_KG:
        if category in legacy:
            return category, True
    return "van", True


class MaintenanceFeatureBuilder:
    def __init__(self, feature_columns: list[str], service_rules: list[dict[str, Any]]):
        if list(feature_columns) != FEATURE_COLUMNS:
            raise ValueError("Feature columns do not match the fleetopt sensor-free schema")
        self.feature_columns = list(feature_columns)
        self.service_rules = [dict(rule) for rule in service_rules]

    @staticmethod
    def default_feature_columns() -> list[str]:
        return list(FEATURE_COLUMNS)

    def build(
        self,
        *,
        vehicle: dict[str, Any],
        trips: list[dict[str, Any]],
        maintenance_records: list[dict[str, Any]],
        inspections: list[dict[str, Any]],
        as_of: datetime | None = None,
    ) -> FeatureBuildResult:
        now = _as_utc(as_of, datetime.now(timezone.utc))
        defaulted: set[str] = set()
        fuel_type = str(vehicle.get("fuel_type") or "electric").lower()
        if fuel_type not in {"electric", "hybrid", "diesel", "petrol"}:
            fuel_type = "electric"
            defaulted.add("fuel_type")
        category, category_defaulted = _category(vehicle)
        if category_defaulted:
            defaulted.add("vehicle_category")

        year = int(vehicle.get("year") or now.year)
        in_service_value = vehicle.get("in_service_date")
        if isinstance(in_service_value, datetime):
            in_service_date = _as_utc(in_service_value, now)
        else:
            in_service_date = datetime(max(min(year, now.year), 1970), 1, 1, tzinfo=timezone.utc)
            defaulted.add("in_service_date")
        payload_capacity = vehicle.get("payload_capacity_kg")
        if payload_capacity is None or float(payload_capacity) <= 0:
            payload_capacity = DEFAULT_PAYLOAD_KG[category]
            defaulted.add("payload_capacity_kg")
        payload_capacity = float(payload_capacity)
        odometer = max(float(vehicle.get("current_mileage") or vehicle.get("current_odometer_km") or 0), 0.0)

        normalized_trips: list[dict[str, Any]] = []
        for trip in trips:
            ended_at = _as_utc(trip.get("ended_at") or trip.get("created_at"), now)
            if ended_at > now:
                continue
            distance = max(float(trip.get("trip_distance_km") or 0), 0.0)
            weight = max(float(trip.get("parcel_weight_kg") or trip.get("parcel_weight") or 0), 0.0)
            roughness = trip.get("route_roughness_index")
            normalized_trips.append({
                **trip,
                "ended_at": ended_at,
                "trip_distance_km": distance,
                "load_ratio": min(weight / payload_capacity, 1.5) if payload_capacity else 0.0,
                "route_roughness_index": float(roughness) if roughness is not None else 2.5,
            })
            if roughness is None:
                defaulted.add("route_roughness")
        normalized_trips.sort(key=lambda row: row["ended_at"])
        if not normalized_trips:
            defaulted.add("trip_history")

        def recent_trips(days: int) -> list[dict[str, Any]]:
            return [row for row in normalized_trips if _days_between(now, row["ended_at"]) <= days]

        trips_7 = recent_trips(7)
        trips_30 = recent_trips(30)
        trips_90 = recent_trips(90)
        distance_7 = sum(row["trip_distance_km"] for row in trips_7)
        distance_30 = sum(row["trip_distance_km"] for row in trips_30)
        distance_90 = sum(row["trip_distance_km"] for row in trips_90)
        latest_trip_distance = normalized_trips[-1]["trip_distance_km"] if normalized_trips else 0.0
        average_load = sum(row["load_ratio"] for row in trips_30) / len(trips_30) if trips_30 else 0.0
        average_roughness = (
            sum(row["route_roughness_index"] for row in trips_30) / len(trips_30) if trips_30 else 2.5
        )

        completed: list[dict[str, Any]] = []
        for record in maintenance_records:
            if record.get("status") not in {None, "completed"}:
                continue
            event_date = _as_utc(record.get("service_date") or record.get("completed_at"), in_service_date)
            if event_date > now:
                continue
            completed.append({
                **record,
                "event_date": event_date,
                "event_kind": _event_kind(record),
                "odometer_km": max(float(record.get("mileage_at_service") or 0), 0.0),
                "maintenance_system": str(record.get("maintenance_system") or "").lower(),
            })
        completed.sort(key=lambda row: row["event_date"])
        if not completed:
            defaulted.add("maintenance_history")
        latest_maintenance = completed[-1] if completed else None
        last_maintenance_date = latest_maintenance["event_date"] if latest_maintenance else in_service_date
        last_maintenance_km = latest_maintenance["odometer_km"] if latest_maintenance else 0.0
        unplanned = [row for row in completed if row["event_kind"] in UNPLANNED_EVENT_KINDS]
        latest_unplanned = unplanned[-1] if unplanned else None
        last_unplanned_date = latest_unplanned["event_date"] if latest_unplanned else in_service_date
        last_unplanned_km = latest_unplanned["odometer_km"] if latest_unplanned else 0.0

        latest_inspection = max(
            (row for row in inspections if _as_utc(row.get("created_at"), now) <= now),
            key=lambda row: _as_utc(row.get("created_at"), now),
            default=None,
        )
        if latest_inspection is None:
            defaulted.add("inspection_history")
        observations = dict((latest_inspection or {}).get("observations") or {})

        rules = [row for row in self.service_rules if str(row.get("fuel_type")).lower() == fuel_type]
        if not rules:
            raise ValueError(f"No maintenance service rules are available for fuel type {fuel_type}")
        failure_exposure: dict[str, float] = {}
        service_usage: dict[str, float] = {}
        service_remaining_km: dict[str, float] = {}
        service_remaining_days: dict[str, float] = {}
        for rule in rules:
            system = str(rule["maintenance_system"])
            system_records = [row for row in completed if row["maintenance_system"] == system]
            system_unplanned = [row for row in system_records if row["event_kind"] in UNPLANNED_EVENT_KINDS]
            failure_reset_km = system_unplanned[-1]["odometer_km"] if system_unplanned else 0.0
            service_reset_km = system_records[-1]["odometer_km"] if system_records else 0.0
            service_reset_date = system_records[-1]["event_date"] if system_records else in_service_date
            failure_life = max(float(rule["simulation_failure_life_km"]), 1.0)
            interval_km = max(float(rule["scheduled_interval_km"]), 1.0)
            interval_days = max(float(rule["scheduled_interval_days"]), 1.0)
            failure_exposure[system] = max(odometer - failure_reset_km, 0.0) / failure_life
            elapsed_km = max(odometer - service_reset_km, 0.0)
            elapsed_days = _days_between(now, service_reset_date)
            service_usage[system] = max(elapsed_km / interval_km, elapsed_days / interval_days)
            service_remaining_km[system] = interval_km - elapsed_km
            service_remaining_days[system] = interval_days - elapsed_days

        ranked_failure = sorted(failure_exposure, key=failure_exposure.get, reverse=True)
        while len(ranked_failure) < 3:
            ranked_failure.append(ranked_failure[-1])
        most_due = max(service_usage, key=service_usage.get)
        top_exposure = failure_exposure[ranked_failure[0]]
        expected_km = max(
            float(next(row["simulation_failure_life_km"] for row in rules if row["maintenance_system"] == ranked_failure[0]))
            * (1.0 - top_exposure),
            0.0,
        )
        average_daily_km = distance_30 / 30 if distance_30 > 0 else odometer / max(_days_between(now, in_service_date), 1.0)
        expected_days = expected_km / max(average_daily_km, 1.0)

        values: dict[str, Any] = {
            "fuel_type": fuel_type,
            "vehicle_category": category,
            # Training data defines age from manufacture year; commissioning only resets service-day exposure.
            "vehicle_age_years": float(max(now.year - year, 0)),
            "current_odometer_km": round(odometer, 3),
            "trip_distance_km": round(latest_trip_distance, 3),
            "distance_last_7d_km": round(distance_7, 3),
            "distance_last_30d_km": round(distance_30, 3),
            "distance_last_90d_km": round(distance_90, 3),
            "trip_count_last_30d": len(trips_30),
            "average_load_ratio_30d": round(average_load, 5),
            "average_route_roughness_30d": round(average_roughness, 4),
            "days_since_last_maintenance": round(_days_between(now, last_maintenance_date), 4),
            "km_since_last_maintenance": round(max(odometer - last_maintenance_km, 0.0), 3),
            "maintenance_count_90d": sum(_days_between(now, row["event_date"]) <= 90 for row in completed),
            "maintenance_count_365d": sum(_days_between(now, row["event_date"]) <= 365 for row in completed),
            "unplanned_repair_count_365d": sum(
                row["event_kind"] in UNPLANNED_EVENT_KINDS and _days_between(now, row["event_date"]) <= 365
                for row in completed
            ),
            "breakdown_count_365d": sum(
                row["event_kind"] == "breakdown" and _days_between(now, row["event_date"]) <= 365
                for row in completed
            ),
            "lifetime_unplanned_repairs": len(unplanned),
            "days_since_last_unplanned_repair": round(_days_between(now, last_unplanned_date), 4),
            "km_since_last_unplanned_repair": round(max(odometer - last_unplanned_km, 0.0), 3),
            "highest_failure_exposure_system": ranked_failure[0],
            "highest_failure_exposure_ratio": round(failure_exposure[ranked_failure[0]], 6),
            "second_failure_exposure_system": ranked_failure[1],
            "second_failure_exposure_ratio": round(failure_exposure[ranked_failure[1]], 6),
            "third_failure_exposure_system": ranked_failure[2],
            "third_failure_exposure_ratio": round(failure_exposure[ranked_failure[2]], 6),
            "overexposed_system_count": sum(value >= 0.85 for value in failure_exposure.values()),
            "expected_failure_km_remaining": round(expected_km, 3),
            "expected_failure_days_remaining": round(expected_days, 4),
            "most_due_service_system": most_due,
            "maximum_service_usage_ratio": round(service_usage[most_due], 6),
            "overdue_service_system_count": sum(value >= 1.0 for value in service_usage.values()),
            "days_until_next_scheduled_service": round(min(service_remaining_days.values()), 4),
            "km_until_next_scheduled_service": round(min(service_remaining_km.values()), 3),
            **{f"{system}_failure_exposure_ratio": round(failure_exposure.get(system, -1.0), 6) for system in SYSTEMS},
            "brake_condition": _condition(observations.get("brake_condition") or observations.get("brake_condition_change")),
            "tire_condition": _condition(observations.get("tire_condition") or observations.get("tire_condition_change")),
            "powertrain_condition": _condition(observations.get("powertrain_condition")),
            "warning_light_level": _condition(observations.get("warning_light_level") or observations.get("dashboard_warning")),
            "charging_or_fuel_issue": _condition(observations.get("charging_or_fuel_issue") or observations.get("charging_condition") or observations.get("charging_problem")),
            "unusual_noise": _condition(observations.get("unusual_noise")),
            "vibration_level": _condition(observations.get("vibration_level") or observations.get("unusual_vibration")),
            "vehicle_damage": _condition(observations.get("vehicle_damage")),
        }
        ordered = {column: values[column] for column in self.feature_columns}
        canonical = json.dumps(ordered, sort_keys=True, separators=(",", ":"), allow_nan=False)
        feature_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        quality_grade = "good" if len(defaulted) <= 1 else "fair" if len(defaulted) <= 4 else "limited"
        source_ids = {
            "trip_ids": [serialize_object_id(row.get("_id") or row.get("trip_id")) for row in normalized_trips if row.get("_id") or row.get("trip_id")],
            "maintenance_record_ids": [serialize_object_id(row["_id"]) for row in completed if row.get("_id")],
            "inspection_ids": [serialize_object_id(row["_id"]) for row in inspections if row.get("_id")],
        }
        return FeatureBuildResult(
            features=ordered,
            feature_hash=feature_hash,
            defaulted_fields=sorted(defaulted),
            quality_grade=quality_grade,
            source_ids=source_ids,
        )


async def build_vehicle_features(vehicle_id: str, as_of: datetime | None = None) -> FeatureBuildResult:
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    try:
        vehicle_oid = validate_object_id(vehicle_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle_id") from exc
    now = _as_utc(as_of, datetime.now(timezone.utc))
    vehicle = await db[VEHICLE_COLLECTION].find_one({"_id": vehicle_oid})
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    inspections = await db[VEHICLE_TRIP_INSPECTION_COLLECTION].find(
        {"vehicle_id": vehicle_oid, "created_at": {"$lte": now}}
    ).sort("created_at", 1).to_list(length=5000)
    maintenance = await db[MAINTENANCE_COLLECTION].find(
        {"vehicle_id": vehicle_oid, "service_date": {"$lte": now}}
    ).sort("service_date", 1).to_list(length=5000)
    post_trips = [row for row in inspections if row.get("inspection_type") == "post_trip"]
    route_ids = [row["route_id"] for row in post_trips if isinstance(row.get("route_id"), ObjectId)]
    routes = await db[ROUTE_PLAN_COLLECTION].find({"_id": {"$in": route_ids}}).to_list(length=len(route_ids) or 1)
    route_by_id = {row["_id"]: row for row in routes}
    delivery_ids = [delivery_id for route in routes for delivery_id in route.get("delivery_order_ids", [])]
    deliveries = await db[DELIVERY_COLLECTION].find({"_id": {"$in": delivery_ids}}).to_list(length=len(delivery_ids) or 1)
    delivery_by_id = {row["_id"]: row for row in deliveries}
    trips: list[dict[str, Any]] = []
    for inspection in post_trips:
        route = route_by_id.get(inspection.get("route_id"), {})
        weight = sum(
            float(delivery_by_id.get(delivery_id, {}).get("parcel_weight") or 0)
            for delivery_id in route.get("delivery_order_ids", [])
        )
        trips.append({
            "_id": inspection.get("trip_session_id") or inspection.get("_id"),
            "ended_at": inspection.get("created_at"),
            "trip_distance_km": inspection.get("trip_distance_km", 0),
            "parcel_weight_kg": weight,
            "route_roughness_index": route.get("route_roughness_index"),
        })

    artifacts = predictive_artifact_registry.get()
    builder = MaintenanceFeatureBuilder(artifacts.feature_columns, artifacts.service_rules)
    return builder.build(
        vehicle=vehicle,
        trips=trips,
        maintenance_records=maintenance,
        inspections=inspections,
        as_of=now,
    )
