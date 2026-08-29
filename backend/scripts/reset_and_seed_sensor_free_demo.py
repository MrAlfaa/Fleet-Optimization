"""Reset operational demo records and seed sensor-free maintenance scenarios.

Authentication, roles, driver accounts, enrolled devices, demand model artifacts,
and demand-zone configuration are intentionally preserved.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bson import ObjectId

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.core.database import close_mongo_connection, connect_to_mongo, get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.delivery_model import DELIVERY_COLLECTION, build_delivery_order_document
from app.models.driver_execution_model import (
    DELIVERY_ATTEMPT_COLLECTION,
    DRIVER_ISSUE_COLLECTION,
    VEHICLE_TRIP_INSPECTION_COLLECTION,
)
from app.models.inspection_model import INSPECTION_COLLECTION
from app.models.maintenance_intelligence_model import (
    FEATURE_SNAPSHOT_COLLECTION,
    PREDICTION_REVIEW_COLLECTION,
)
from app.models.maintenance_model import MAINTENANCE_COLLECTION, build_maintenance_document
from app.models.predictive_model import PREDICTION_COLLECTION
from app.models.route_model import ROUTE_PLAN_COLLECTION, ROUTE_SEGMENT_COLLECTION, build_route_plan_document
from app.models.trip_model import DRIVER_LOCATION_COLLECTION, TRIP_EVENT_COLLECTION, TRIP_SESSION_COLLECTION
from app.models.user_model import USER_COLLECTION, utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION, build_vehicle_document
from app.models.vehicle_part_model import VEHICLE_PART_COLLECTION
from app.services.predictive_artifact_registry import predictive_artifact_registry
from app.services.predictive_maintenance_service import recalculate_vehicle_maintenance


SEED_TAG = "SENSOR-FREE-DEMO-V1"
REQUIRED_RISK_LEVELS = {"low", "medium", "high", "critical"}

# These collections contain operational/demo state. Identity and configuration
# collections are intentionally absent from this list.
RESET_COLLECTIONS = (
    ALERT_COLLECTION,
    DELIVERY_ATTEMPT_COLLECTION,
    DRIVER_ISSUE_COLLECTION,
    DRIVER_LOCATION_COLLECTION,
    FEATURE_SNAPSHOT_COLLECTION,
    INSPECTION_COLLECTION,
    MAINTENANCE_COLLECTION,
    PREDICTION_COLLECTION,
    PREDICTION_REVIEW_COLLECTION,
    ROUTE_PLAN_COLLECTION,
    ROUTE_SEGMENT_COLLECTION,
    TRIP_EVENT_COLLECTION,
    TRIP_SESSION_COLLECTION,
    VEHICLE_PART_COLLECTION,
    VEHICLE_TRIP_INSPECTION_COLLECTION,
    DELIVERY_COLLECTION,
    "operational_demand_daily",
    VEHICLE_COLLECTION,
)


SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "code": "DEMO-EV-LOW", "registration": "WP CAA-4101", "brand": "BYD", "model": "T3",
        "fuel": "electric", "category": "van", "expected_risk": "low", "odometer": 20_000,
        "age_years": 2, "service_gap_km": 1_000, "service_age_days": 10, "condition": "normal",
        "daily_km": 40, "roughness": 2.0, "payload_kg": 1_400, "battery_kwh": 50,
    },
    {
        "code": "DEMO-HY-LOW", "registration": "WP CAB-4102", "brand": "Toyota", "model": "Corolla Cross",
        "fuel": "hybrid", "category": "car", "expected_risk": "low", "odometer": 28_000,
        "age_years": 2, "service_gap_km": 1_000, "service_age_days": 10, "condition": "normal",
        "daily_km": 40, "roughness": 2.0, "payload_kg": 450,
    },
    {
        "code": "DEMO-PT-LOW", "registration": "WP CAC-4103", "brand": "Toyota", "model": "HiAce",
        "fuel": "petrol", "category": "van", "expected_risk": "low", "odometer": 120_000,
        "age_years": 12, "service_gap_km": 10_000, "service_age_days": 90, "condition": "normal",
        "daily_km": 60, "roughness": 5.0, "payload_kg": 1_400,
    },
    {
        "code": "DEMO-DS-LOW", "registration": "WP CAD-4104", "brand": "Isuzu", "model": "N-Series",
        "fuel": "diesel", "category": "truck", "expected_risk": "low", "odometer": 120_000,
        "age_years": 12, "service_gap_km": 10_000, "service_age_days": 90, "condition": "normal",
        "daily_km": 60, "roughness": 5.0, "payload_kg": 6_500,
    },
    {
        "code": "DEMO-EV-MED", "registration": "WP CAE-4105", "brand": "Maxus", "model": "eDeliver 3",
        "fuel": "electric", "category": "truck", "expected_risk": "medium", "odometer": 180_000,
        "age_years": 2, "service_gap_km": 1_000, "service_age_days": 10, "condition": "normal",
        "daily_km": 40, "roughness": 2.0, "payload_kg": 6_500, "battery_kwh": 52,
    },
    {
        "code": "DEMO-HY-MED", "registration": "WP CAF-4106", "brand": "Mitsubishi", "model": "Fuso Canter Eco Hybrid",
        "fuel": "hybrid", "category": "truck", "expected_risk": "medium", "odometer": 180_000,
        "age_years": 2, "service_gap_km": 1_000, "service_age_days": 10, "condition": "normal",
        "daily_km": 40, "roughness": 2.0, "payload_kg": 6_500,
    },
    {
        "code": "DEMO-DS-HIGH", "registration": "WP CAG-4107", "brand": "Ashok Leyland", "model": "Partner",
        "fuel": "diesel", "category": "truck", "expected_risk": "high", "odometer": 180_000,
        "age_years": 2, "service_gap_km": 1_000, "service_age_days": 10, "condition": "normal",
        "daily_km": 40, "roughness": 3.5, "payload_kg": 6_500,
    },
    {
        "code": "DEMO-PT-CRIT", "registration": "WP CAH-4108", "brand": "Toyota", "model": "Coaster",
        "fuel": "petrol", "category": "bus", "expected_risk": "critical", "odometer": 180_000,
        "age_years": 2, "service_gap_km": 1_000, "service_age_days": 10, "condition": "normal",
        "daily_km": 40, "roughness": 3.5, "payload_kg": 8_500,
    },
)


def _observations(condition: str) -> dict[str, Any]:
    return {
        "brake_condition": condition,
        "tire_condition": condition,
        "powertrain_condition": condition,
        "warning_light_level": condition,
        "charging_or_fuel_issue": condition,
        "unusual_noise": condition,
        "vibration_level": condition,
        "vehicle_damage": condition,
    }


async def _reset_operational_data(db) -> dict[str, int]:
    before: dict[str, int] = {}
    for collection_name in RESET_COLLECTIONS:
        before[collection_name] = await db[collection_name].count_documents({})
        await db[collection_name].delete_many({})
    return before


async def _seed_vehicle_history(db, scenario: dict[str, Any], admin_id: ObjectId) -> ObjectId:
    now = utc_now()
    in_service_date = now - timedelta(days=365 * int(scenario["age_years"]))
    vehicle = build_vehicle_document({
        "vehicle_code": scenario["code"],
        "registration_number": scenario["registration"],
        "vehicle_type": f"{scenario['fuel']}_{scenario['category']}",
        "vehicle_category": scenario["category"],
        "brand": scenario["brand"],
        "model": scenario["model"],
        "year": now.year - int(scenario["age_years"]),
        "fuel_type": scenario["fuel"],
        "current_mileage": scenario["odometer"],
        "in_service_date": in_service_date,
        "payload_capacity_kg": scenario["payload_kg"],
        "battery_capacity_kwh": scenario.get("battery_kwh"),
        "status": "active",
        "health_status": "healthy",
        "image_url": None,
    })
    vehicle_id = (await db[VEHICLE_COLLECTION].insert_one(vehicle)).inserted_id

    artifacts = predictive_artifact_registry.get()
    applicable_systems = sorted({
        str(rule["maintenance_system"])
        for rule in artifacts.service_rules
        if str(rule["fuel_type"]) == scenario["fuel"]
    })
    completed_date = now - timedelta(days=int(scenario["service_age_days"]))
    for system in applicable_systems:
        record = build_maintenance_document({
            "vehicle_id": vehicle_id,
            "part_name": system.replace("_", " ").title(),
            "maintenance_type": "preventive",
            "maintenance_system": system,
            "event_kind": "scheduled_service",
            "issue_type": "Scheduled service completed",
            "service_date": completed_date,
            "mileage_at_service": max(float(scenario["odometer"]) - float(scenario["service_gap_km"]), 0),
            "technician_name": "Colombo Fleet Service Team",
            "service_center": "FleetOpt Colombo Workshop",
            "cost": 18_500,
            "actual_cost": 18_500,
            "status": "completed",
            "priority": "medium",
            "notes": f"{SEED_TAG} completed service history",
            "work_order_status": "completed",
            "completed_at": completed_date,
            "completed_by": admin_id,
            "completion_evidence": "Service checklist completed and road test passed.",
        }, admin_id)
        await db[MAINTENANCE_COLLECTION].insert_one(record)

    if scenario["expected_risk"] in {"high", "critical"}:
        priority = "critical" if scenario["expected_risk"] == "critical" else "high"
        await db[MAINTENANCE_COLLECTION].insert_one(build_maintenance_document({
            "vehicle_id": vehicle_id,
            "part_name": "Focused Vehicle Inspection",
            "maintenance_type": "inspection",
            "maintenance_system": applicable_systems[0],
            "event_kind": "inspection",
            "issue_type": "Assessment follow-up inspection",
            "service_date": now + timedelta(days=2),
            "mileage_at_service": scenario["odometer"],
            "technician_name": "Unassigned",
            "service_center": "FleetOpt Colombo Workshop",
            "status": "scheduled",
            "priority": priority,
            "notes": f"{SEED_TAG} open service work",
            "work_order_status": "planned",
        }, admin_id))

    trip_days = (27, 15, 6, 2)
    for trip_index, days_ago in enumerate(trip_days, start=1):
        delivery = build_delivery_order_document({
            "order_code": f"{scenario['code']}-ORD-{trip_index}",
            "customer_name": "FleetOpt Demo Customer",
            "customer_phone": "0770000000",
            "pickup_latitude": 6.9271,
            "pickup_longitude": 79.8612,
            "drop_latitude": 6.9016,
            "drop_longitude": 79.9583,
            "pickup_address": "Colombo Central Depot",
            "drop_address": "Nugegoda Service Zone",
            "zone_id": "LK_nugegoda",
            "operational_zone_id": "LK_nugegoda",
            "zone_assignment_method": "confirmed",
            "parcel_weight": float(scenario["payload_kg"]) * 0.55,
            "parcel_volume": 1.2,
            "priority": "medium",
            "delivery_status": "delivered",
            "assigned_vehicle_id": vehicle_id,
            "scheduled_date": now - timedelta(days=days_ago),
            "is_demo": True,
        })
        delivery_id = (await db[DELIVERY_COLLECTION].insert_one(delivery)).inserted_id
        route = build_route_plan_document({
            "route_code": f"{scenario['code']}-R-{trip_index}",
            "route_name": f"{SEED_TAG} completed trip",
            "vehicle_id": vehicle_id,
            "driver_id": None,
            "depot_latitude": 6.9271,
            "depot_longitude": 79.8612,
            "depot_name": "Colombo Central Depot",
            "delivery_order_ids": [delivery_id],
            "optimized_stop_order": [str(delivery_id)],
            "status": "completed",
            "completed_at": now - timedelta(days=days_ago),
            "created_by": admin_id,
        })
        route["route_roughness_index"] = float(scenario["roughness"])
        route_id = (await db[ROUTE_PLAN_COLLECTION].insert_one(route)).inserted_id
        await db[VEHICLE_TRIP_INSPECTION_COLLECTION].insert_one({
            "route_id": route_id,
            "driver_id": admin_id,
            "vehicle_id": vehicle_id,
            "inspection_type": "post_trip",
            "observations": _observations(str(scenario["condition"])),
            "safety_blocking": False,
            "trip_distance_km": float(scenario["daily_km"]) * 7,
            "created_at": now - timedelta(days=days_ago),
            "updated_at": now - timedelta(days=days_ago),
            "created_by": admin_id,
            "seed_tag": SEED_TAG,
        })
    return vehicle_id


async def reset_and_seed() -> int:
    await connect_to_mongo()
    try:
        db = get_database()
        if db is None:
            print("MongoDB is not configured. Configure backend/.env first.")
            return 1
        await db.command("ping")
        admin = await db[USER_COLLECTION].find_one({"role": "admin", "is_active": {"$ne": False}})
        if admin is None:
            print("No active admin exists. Create an admin before seeding demo data.")
            return 1

        users_before = await db[USER_COLLECTION].count_documents({})
        devices_before = await db["driver_devices"].count_documents({})
        removed = await _reset_operational_data(db)
        current_user = {"id": str(admin["_id"]), "role": "admin", "email": admin.get("email")}

        actual_results: list[dict[str, Any]] = []
        for scenario in SCENARIOS:
            vehicle_id = await _seed_vehicle_history(db, scenario, admin["_id"])
            prediction = await recalculate_vehicle_maintenance(
                str(vehicle_id),
                {"trigger": "imported", "notes": f"{SEED_TAG} initial assessment"},
                current_user,
            )
            actual_results.append({
                "vehicle": scenario["registration"],
                "expected": scenario["expected_risk"],
                "actual": prediction["risk_level"],
                "probability_30_days": round(float(prediction["failure_probability_30_days"]), 4),
                "probability_2000_km": round(float(prediction["failure_probability_2000_km"]), 4),
            })
            print(
                f"ASSESSED {scenario['registration']}: expected={scenario['expected_risk']} "
                f"actual={prediction['risk_level']}"
            )

        users_after = await db[USER_COLLECTION].count_documents({})
        devices_after = await db["driver_devices"].count_documents({})
        if users_after != users_before or devices_after != devices_before:
            raise RuntimeError("Safety check failed: identity or device records changed")

        distribution = Counter(item["actual"] for item in actual_results)
        mismatches = [item for item in actual_results if item["actual"] != item["expected"]]
        print("\nSENSOR-FREE DEMO RESET COMPLETE")
        print(f"database: {settings.mongodb_db_name}")
        print(f"users_preserved: {users_after}")
        print(f"driver_devices_preserved: {devices_after}")
        print(f"removed_records: {sum(removed.values())}")
        print(f"vehicles_created: {await db[VEHICLE_COLLECTION].count_documents({})}")
        print(f"maintenance_records_created: {await db[MAINTENANCE_COLLECTION].count_documents({})}")
        print(f"trip_history_records_created: {await db[VEHICLE_TRIP_INSPECTION_COLLECTION].count_documents({})}")
        print(f"predictions_created: {await db[PREDICTION_COLLECTION].count_documents({})}")
        print(f"risk_distribution: {dict(sorted(distribution.items()))}")
        if mismatches:
            print(f"risk_expectation_mismatches: {mismatches}")
        missing_levels = REQUIRED_RISK_LEVELS - set(distribution)
        if missing_levels:
            print(f"ERROR missing risk levels: {sorted(missing_levels)}")
            return 2
        return 0
    finally:
        await close_mongo_connection()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-reset",
        action="store_true",
        help="Required acknowledgement that operational demo collections will be cleared.",
    )
    args = parser.parse_args()
    if not args.confirm_reset:
        parser.error("--confirm-reset is required; users and identity data are still preserved")
    return asyncio.run(reset_and_seed())


if __name__ == "__main__":
    raise SystemExit(main())
