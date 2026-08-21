"""Seed admin-only QA data without creating users, drivers, or assignments."""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import close_mongo_connection, connect_to_mongo, get_database
from app.models.alert_model import ALERT_COLLECTION, build_alert_document, ensure_alert_indexes
from app.models.delivery_model import DELIVERY_COLLECTION, ensure_delivery_indexes
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
from app.schemas.predictive_schema import EVSensorInput, PredictiveMaintenanceRequest
from app.services.delivery_service import create_delivery_order
from app.services.demand_forecasting_service import import_artifact_forecasts_to_database, refresh_forecast_from_model
from app.services.operational_demand_service import rebuild_operational_demand
from app.services.predictive_maintenance_service import predict_vehicle_maintenance
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


def _prediction_scenario(index: int, mileage: float) -> dict[str, Any]:
    stress = index / max(len(VEHICLE_SCENARIOS) - 1, 1)
    return {
        "SoC": round(86 - stress * 58, 2),
        "SoH": round(97 - stress * 28, 2),
        "Battery_Voltage": round(402 - stress * 42, 2),
        "Battery_Current": round(34 + stress * 92, 2),
        "Battery_Temperature": round(29 + stress * 25, 2),
        "Charge_Cycles": round(180 + stress * 980, 2),
        "Motor_Temperature": round(55 + stress * 52, 2),
        "Motor_Vibration": round(0.12 + stress * 1.45, 3),
        "Motor_Torque": round(140 + stress * 110, 2),
        "Motor_RPM": round(2200 + stress * 2400, 2),
        "Power_Consumption": round(17 + stress * 24, 2),
        "Brake_Pad_Wear": round(12 + stress * 76, 2),
        "Brake_Pressure": round(62 - stress * 19, 2),
        "Reg_Brake_Efficiency": round(91 - stress * 34, 2),
        "Tire_Pressure": round(35 - stress * 7, 2),
        "Tire_Temperature": round(30 + stress * 24, 2),
        "Suspension_Load": round(68 + stress * 64, 2),
        "Driving_Speed": round(38 + stress * 34, 2),
        "Distance_Traveled": float(mileage),
        "Route_Roughness": round(0.12 + stress * 0.77, 3),
        "Ambient_Temperature": round(28 + stress * 7, 2),
        "Ambient_Humidity": round(63 + stress * 19, 2),
        "Load_Weight": round(180 + stress * 930, 2),
        "Idle_Time": round(8 + stress * 46, 2),
        "hour": 8 + index,
        "day_of_week": index % 7,
        "month": datetime.now(timezone.utc).month,
        "is_weekend": 1 if index % 7 in {5, 6} else 0,
    }


PREDICTION_SCENARIOS = [
    _prediction_scenario(index, vehicle["current_mileage"])
    for index, vehicle in enumerate(VEHICLE_SCENARIOS)
]


DELIVERY_SCENARIOS: list[dict[str, Any]] = []
for zone_index, zone in enumerate(operational_zone_options()):
    for item_index in range(2):
        offset = 0.006 * (item_index + 1)
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
                "parcel_volume": round(0.05 + item_index * 0.03, 2),
                "priority": ["low", "medium", "high", "urgent"][(zone_index + item_index) % 4],
                "delivery_status": "pending",
                "is_demo": False,
                "scheduled_date": utc_now() + timedelta(days=(zone_index + item_index) % 7),
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
        vehicle = await db[VEHICLE_COLLECTION].find_one({"vehicle_code": scenario["vehicle_code"]})
        if vehicle is None:
            document = build_vehicle_document({
                **scenario,
                "fuel_type": "electric",
                "status": "active",
                "health_status": "unknown",
            })
            result = await db[VEHICLE_COLLECTION].insert_one(document)
            vehicle = await db[VEHICLE_COLLECTION].find_one({"_id": result.inserted_id})
            print(f"CREATED vehicle {scenario['registration_number']}")
        else:
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
    for vehicle, sensor_data in zip(vehicles, PREDICTION_SCENARIOS, strict=True):
        if await db[PREDICTION_COLLECTION].find_one({"vehicle_id": vehicle["_id"]}):
            continue
        try:
            await predict_vehicle_maintenance(PredictiveMaintenanceRequest(
                vehicle_id=str(vehicle["_id"]),
                input_source="imported",
                sensor_data=EVSensorInput(**sensor_data),
            ), current_user)
            created += 1
        except Exception as exc:
            errors.append(f"{vehicle['vehicle_code']}: {exc}")
    return created, errors


async def _seed_deliveries(db, current_user: dict[str, Any]) -> int:
    created = 0
    for scenario in DELIVERY_SCENARIOS:
        if await db[DELIVERY_COLLECTION].find_one({"order_code": scenario["order_code"]}):
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
