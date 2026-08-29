"""Seed admin-only QA data without creating users, drivers, or assignments."""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import close_mongo_connection, connect_to_mongo, get_database
from app.models.alert_model import ALERT_COLLECTION, build_alert_document, ensure_alert_indexes
from app.models.delivery_model import DELIVERY_COLLECTION, build_delivery_order_document, ensure_delivery_indexes
from app.models.demand_model import DEMAND_FORECAST_COLLECTION, DEMAND_ZONE_COLLECTION, ensure_demand_indexes
from app.models.maintenance_model import MAINTENANCE_COLLECTION, build_maintenance_document, ensure_maintenance_indexes
from app.models.predictive_model import PREDICTION_COLLECTION, ensure_prediction_indexes
from app.models.route_model import ROUTE_PLAN_COLLECTION, ensure_route_indexes
from app.models.user_model import USER_COLLECTION, utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION, build_vehicle_document, ensure_vehicle_indexes
from app.models.vehicle_part_model import (
    DEFAULT_EV_PARTS,
    VEHICLE_PART_COLLECTION,
    build_vehicle_part_document,
    ensure_vehicle_part_indexes,
)
from app.services.delivery_service import create_delivery_order
from app.services.demand_forecasting_service import import_artifact_forecasts_to_database, refresh_forecast_from_model
from app.services.operational_demand_service import rebuild_operational_demand
from app.services.predictive_maintenance_service import recalculate_vehicle_maintenance
from app.utils.sri_lanka_zones import operational_zone_options


SEED_TAG = "SYSTEM-QA-SEED"

VEHICLE_SCENARIOS = [
    {"vehicle_code": "QA-EV-001", "registration_number": "WP CAA-1201", "vehicle_type": "electric_van", "brand": "BYD", "model": "T3", "year": 2024, "current_mileage": 18420, "battery_capacity_kwh": 50},
    {"vehicle_code": "QA-EV-002", "registration_number": "WP CAA-1202", "vehicle_type": "electric_van", "brand": "Nissan", "model": "e-NV200", "year": 2023, "current_mileage": 32780, "battery_capacity_kwh": 40},
    {"vehicle_code": "QA-EV-003", "registration_number": "CP CAA-2203", "vehicle_type": "electric_truck", "brand": "Maxus", "model": "eDeliver 3", "year": 2024, "current_mileage": 24600, "battery_capacity_kwh": 52},
    {"vehicle_code": "QA-EV-004", "registration_number": "SP CAA-3204", "vehicle_type": "electric_van", "brand": "Mercedes", "model": "eSprinter", "year": 2023, "current_mileage": 41850, "battery_capacity_kwh": 55},
    {"vehicle_code": "QA-EV-005", "registration_number": "NW CAA-4205", "vehicle_type": "electric_car", "brand": "Hyundai", "model": "Kona Electric", "year": 2024, "current_mileage": 15900, "battery_capacity_kwh": 64},
    {"vehicle_code": "QA-EV-006", "registration_number": "WP CAA-1206", "vehicle_type": "electric_car", "brand": "MG", "model": "ZS EV", "year": 2022, "current_mileage": 53600, "battery_capacity_kwh": 50},
    {"vehicle_code": "QA-EV-007", "registration_number": "EP CAA-5207", "vehicle_type": "electric_van", "brand": "Renault", "model": "Kangoo E-Tech", "year": 2023, "current_mileage": 28950, "battery_capacity_kwh": 45},
    {"vehicle_code": "QA-EV-008", "registration_number": "WP CAA-1208", "vehicle_type": "electric_bus", "brand": "BYD", "model": "K9", "year": 2022, "current_mileage": 68400, "battery_capacity_kwh": 324},
]

VEHICLE_LOAD_DEFAULTS = {
    "car": {"profile_code": "COMPACT_CAR", "capacity_m3": 1.764, "cargo_length_cm": 160, "cargo_width_cm": 105, "cargo_height_cm": 105, "max_parcels": 18, "max_stack_layers": 2, "vehicle_max_stack_weight_kg": 60, "payload_capacity_kg": 420},
    "van": {"profile_code": "MEDIUM_VAN", "capacity_m3": 9.52, "cargo_length_cm": 320, "cargo_width_cm": 170, "cargo_height_cm": 175, "max_parcels": 70, "max_stack_layers": 4, "vehicle_max_stack_weight_kg": 300, "payload_capacity_kg": 1200},
    "truck": {"profile_code": "MEDIUM_TRUCK", "capacity_m3": 24.948, "cargo_length_cm": 540, "cargo_width_cm": 220, "cargo_height_cm": 210, "max_parcels": 180, "max_stack_layers": 6, "vehicle_max_stack_weight_kg": 900, "payload_capacity_kg": 4500},
    "bus": {"profile_code": "HEAVY_BUS", "capacity_m3": 23.94, "cargo_length_cm": 600, "cargo_width_cm": 210, "cargo_height_cm": 190, "max_parcels": 140, "max_stack_layers": 5, "vehicle_max_stack_weight_kg": 600, "payload_capacity_kg": 3000},
}


PREDICTION_SCENARIOS = [
    {"trigger": "imported", "notes": f"{SEED_TAG} server-derived risk scenario {index + 1}"}
    for index, _vehicle in enumerate(VEHICLE_SCENARIOS)
]


DELIVERY_SCENARIOS: list[dict[str, Any]] = []
for zone_index, zone in enumerate(operational_zone_options()):
    for item_index in range(2):
        offset = 0.006 * (item_index + 1)
        length_cm = 42 + (zone_index % 4) * 8 + item_index * 12
        width_cm = 30 + (zone_index % 3) * 7 + item_index * 8
        height_cm = 24 + (zone_index % 5) * 5 + item_index * 10
        fragile = (zone_index + item_index) % 5 == 0
        DELIVERY_SCENARIOS.append(
            {
                "order_code": f"QA-ORD-{zone_index + 1:02d}-{item_index + 1:02d}",
                "customer_name": f"QA Customer {zone_index + 1}-{item_index + 1}",
                "customer_phone": f"077000{zone_index:02d}{item_index}",
                "pickup_latitude": 6.9271,
                "pickup_longitude": 79.8612,
                "drop_latitude": float(zone["zone_lat"]) + offset,
                "drop_longitude": float(zone["zone_lng"]) + offset,
                "pickup_address": "FleetOpt Colombo Test Depot",
                "drop_address": f"QA delivery point, {zone['zone_display_name']}",
                "zone_id": zone["operational_zone_id"],
                "zone_assignment_method": "confirmed",
                "parcel_weight": round(4.5 + zone_index * 1.7 + item_index, 2),
                "parcel_volume": round((length_cm * width_cm * height_cm) / 1_000_000, 8),
                "load_profile": {
                    "length_cm": length_cm,
                    "width_cm": width_cm,
                    "height_cm": height_cm,
                    "fragile": fragile,
                    "stackable": not fragile,
                    "max_stack_weight_kg": 0 if fragile else 35,
                    "loading_orientation_fixed": fragile,
                    "do_not_tilt": fragile,
                    "service_type": "door_to_door",
                },
                "priority": ["low", "medium", "high", "urgent"][(zone_index + item_index) % 4],
                "delivery_status": "pending",
                "is_demo": True,
                "delivery_date": utc_now().date().isoformat(),
                "delivery_period": "first_half" if item_index == 0 else "second_half",
            }
        )


async def _ensure_indexes() -> None:
    await ensure_vehicle_indexes()
    await ensure_vehicle_part_indexes()
    await ensure_maintenance_indexes()
    await ensure_alert_indexes()
    await ensure_prediction_indexes()
    await ensure_delivery_indexes()
    await ensure_demand_indexes()
    await ensure_route_indexes()


async def _seed_vehicles(db) -> list[dict[str, Any]]:
    vehicles: list[dict[str, Any]] = []
    for scenario in VEHICLE_SCENARIOS:
        category = scenario["vehicle_type"].rsplit("_", 1)[-1]
        load_defaults = VEHICLE_LOAD_DEFAULTS[category]
        canonical = {
            "vehicle_category": category,
            "payload_capacity_kg": load_defaults["payload_capacity_kg"],
            "in_service_date": f"{scenario['year']}-01-01",
            "is_demo": True,
            "load_profile": {
                **{key: value for key, value in load_defaults.items() if key != "payload_capacity_kg"},
                "is_refrigerated": False,
                "is_hazmat_certified": category == "truck",
                "has_tail_lift": category in {"van", "truck"},
                "available_from": "08:00",
                "available_until": "17:00",
            },
        }
        vehicle = await db[VEHICLE_COLLECTION].find_one({"vehicle_code": scenario["vehicle_code"]})
        if vehicle is None:
            document = build_vehicle_document({
                **scenario,
                **canonical,
                "fuel_type": "electric",
                "status": "active",
                "health_status": "unknown",
            })
            result = await db[VEHICLE_COLLECTION].insert_one(document)
            vehicle = await db[VEHICLE_COLLECTION].find_one({"_id": result.inserted_id})
            print(f"CREATED vehicle {scenario['registration_number']}")
        else:
            await db[VEHICLE_COLLECTION].update_one(
                {"_id": vehicle["_id"]},
                {"$set": {**canonical, "updated_at": utc_now()}},
            )
            vehicle = await db[VEHICLE_COLLECTION].find_one({"_id": vehicle["_id"]})
            print(f"SKIPPED existing vehicle {scenario['registration_number']}")
        vehicles.append(vehicle)

        existing_names = {
            row["part_name"]
            for row in await db[VEHICLE_PART_COLLECTION].find({"vehicle_id": vehicle["_id"]}).to_list(length=100)
        }
        for part_name, category in DEFAULT_EV_PARTS:
            if part_name in existing_names:
                continue
            await db[VEHICLE_PART_COLLECTION].insert_one(build_vehicle_part_document(vehicle["_id"], {
                "part_name": part_name,
                "part_category": category,
                "risk_level": "unknown",
                "risk_score": 0,
                "status": "unknown",
                "notes": SEED_TAG,
            }))
    return vehicles


async def _seed_maintenance(db, vehicles: list[dict[str, Any]], admin_id) -> int:
    created = 0
    for index, vehicle in enumerate(vehicles):
        parts = await db[VEHICLE_PART_COLLECTION].find({"vehicle_id": vehicle["_id"]}).sort("part_name", 1).limit(2).to_list(length=2)
        for part_index, part in enumerate(parts):
            note = f"{SEED_TAG}:{vehicle['vehicle_code']}:{part_index}"
            if await db[MAINTENANCE_COLLECTION].find_one({"notes": note}):
                continue
            priority = ["low", "medium", "high", "critical"][(index + part_index) % 4]
            await db[MAINTENANCE_COLLECTION].insert_one(build_maintenance_document({
                "vehicle_id": vehicle["_id"],
                "part_id": part["_id"],
                "part_name": part["part_name"],
                "maintenance_type": ["inspection", "preventive", "predictive", "replacement"][(index + part_index) % 4],
                "issue_type": "QA maintenance workflow verification",
                "service_date": utc_now() + timedelta(days=(index + part_index) - 4),
                "mileage_at_service": vehicle["current_mileage"],
                "technician_name": "QA Fleet Technician",
                "service_center": "Colombo EV Test Service Center",
                "cost": 8500 + index * 1750 + part_index * 950,
                "status": ["scheduled", "in_progress", "completed"][(index + part_index) % 3],
                "priority": priority,
                "notes": note,
            }, admin_id))
            created += 1
    return created


async def _seed_predictions(db, vehicles: list[dict[str, Any]], current_user: dict[str, Any]) -> tuple[int, list[str]]:
    created = 0
    errors: list[str] = []
    for vehicle, trigger_metadata in zip(vehicles, PREDICTION_SCENARIOS, strict=True):
        if await db[PREDICTION_COLLECTION].find_one({"vehicle_id": vehicle["_id"]}):
            continue
        try:
            await recalculate_vehicle_maintenance(str(vehicle["_id"]), trigger_metadata, current_user)
            created += 1
        except Exception as exc:
            errors.append(f"{vehicle['vehicle_code']}: {exc}")
    return created, errors


async def _seed_deliveries(db, current_user: dict[str, Any]) -> int:
    created = 0
    for scenario in DELIVERY_SCENARIOS:
        existing = await db[DELIVERY_COLLECTION].find_one({"order_code": scenario["order_code"]})
        if existing:
            if existing.get("delivery_status") == "pending" and existing.get("load_planning_status", "unplanned") in {"unplanned", "failed"}:
                prepared = build_delivery_order_document(scenario)
                await db[DELIVERY_COLLECTION].update_one(
                    {"_id": existing["_id"]},
                    {"$set": {
                        "parcel_weight": prepared["parcel_weight"],
                        "parcel_volume": prepared["parcel_volume"],
                        "load_profile": prepared["load_profile"],
                        "delivery_date": prepared["delivery_date"],
                        "delivery_period": prepared["delivery_period"],
                        "delivery_window_start": prepared["delivery_window_start"],
                        "delivery_window_end": prepared["delivery_window_end"],
                        "scheduled_date": prepared["scheduled_date"],
                        "is_demo": True,
                        "updated_at": utc_now(),
                    }},
                )
            continue
        await create_delivery_order(scenario, current_user)
        created += 1
    return created


async def _seed_alerts(db, vehicles: list[dict[str, Any]]) -> int:
    created = 0
    for index, vehicle in enumerate(vehicles[:4]):
        title = f"{SEED_TAG} operational alert {index + 1}"
        if await db[ALERT_COLLECTION].find_one({"title": title}):
            continue
        await db[ALERT_COLLECTION].insert_one(build_alert_document({
            "alert_type": "maintenance" if index % 2 == 0 else "system",
            "severity": ["info", "warning", "high", "critical"][index],
            "title": title,
            "message": f"QA alert for {vehicle.get('registration_number')}",
            "linked_vehicle_id": vehicle["_id"],
            "status": "active",
            "created_by_system": True,
        }))
        created += 1
    return created


async def seed_system_test_data() -> int:
    await connect_to_mongo()
    try:
        db = get_database()
        if db is None:
            print("MongoDB is not configured. Configure backend/.env first.")
            return 1
        await db.command("ping")
        admin = await db[USER_COLLECTION].find_one({"role": "admin", "is_active": {"$ne": False}})
        if admin is None:
            print("No active admin exists. Create the admin account before running this seed.")
            return 1

        users_before = await db[USER_COLLECTION].count_documents({})
        drivers_before = await db[USER_COLLECTION].count_documents({"role": "driver"})
        await _ensure_indexes()
        current_user = {"id": str(admin["_id"]), "role": "admin", "email": admin.get("email")}

        vehicles = await _seed_vehicles(db)
        maintenance_created = await _seed_maintenance(db, vehicles, admin["_id"])
        predictions_created, prediction_errors = await _seed_predictions(db, vehicles, current_user)
        deliveries_created = await _seed_deliveries(db, current_user)
        alerts_created = await _seed_alerts(db, vehicles)
        actuals = await rebuild_operational_demand()

        if await db[DEMAND_ZONE_COLLECTION].count_documents({}) == 0:
            imported = await import_artifact_forecasts_to_database(current_user)
        else:
            imported = {"zones_imported": 0, "forecast_records": 0, "planning_records": 0}
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if await db[DEMAND_FORECAST_COLLECTION].count_documents({"forecast_date": {"$gte": today}}) == 0:
            refreshed = await refresh_forecast_from_model(days=30, save_to_database=True, source="model", current_user=current_user)
        else:
            refreshed = {"forecast_records": 0, "planning_records": 0, "fallback_used": False}

        users_after = await db[USER_COLLECTION].count_documents({})
        drivers_after = await db[USER_COLLECTION].count_documents({"role": "driver"})
        if users_after != users_before or drivers_after != drivers_before:
            raise RuntimeError("Safety check failed: the seed changed user or driver counts")

        summary = {
            "users_unchanged": users_after,
            "drivers_unchanged": drivers_after,
            "vehicles": await db[VEHICLE_COLLECTION].count_documents({"vehicle_code": {"$regex": "^QA-EV-"}}),
            "parts": await db[VEHICLE_PART_COLLECTION].count_documents({"vehicle_id": {"$in": [row["_id"] for row in vehicles]}}),
            "maintenance": await db[MAINTENANCE_COLLECTION].count_documents({"notes": {"$regex": f"^{SEED_TAG}"}}),
            "predictions": await db[PREDICTION_COLLECTION].count_documents({"vehicle_id": {"$in": [row["_id"] for row in vehicles]}}),
            "deliveries": await db[DELIVERY_COLLECTION].count_documents({"order_code": {"$regex": "^QA-ORD-"}}),
            "alerts": await db[ALERT_COLLECTION].count_documents({}),
            "demand_forecasts": await db[DEMAND_FORECAST_COLLECTION].count_documents({}),
            "route_plans": await db[ROUTE_PLAN_COLLECTION].count_documents({}),
            "new_maintenance": maintenance_created,
            "new_predictions": predictions_created,
            "new_deliveries": deliveries_created,
            "new_alerts": alerts_created,
            "actual_days_rebuilt": actuals["days_rebuilt"],
            "artifact_records_imported": imported.get("forecast_records", 0),
            "current_forecast_records": refreshed.get("forecast_records", 0),
            "prediction_errors": prediction_errors,
        }
        print("SYSTEM TEST DATA SEED COMPLETE")
        for key, value in summary.items():
            print(f"{key}: {value}")
        return 0 if not prediction_errors else 2
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(seed_system_test_data()))
