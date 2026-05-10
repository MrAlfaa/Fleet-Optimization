import asyncio
import sys
from pathlib import Path

import pandas as pd
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.models.maintenance_model import MAINTENANCE_COLLECTION, build_maintenance_document
from app.models.user_model import USER_COLLECTION, utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION, build_vehicle_document
from app.models.vehicle_part_model import DEFAULT_EV_PARTS, VEHICLE_PART_COLLECTION, build_vehicle_part_document


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "Data_Sets" / "Predictive_Meintains_Data_Set" / "EV_Predictive_Maintenance_Dataset_15min.csv"


CSV_VEHICLES = [
    ("EV-FLEET-CSV-001", "WP-EVC-6001", "BYD", "T3"),
    ("EV-FLEET-CSV-002", "WP-EVC-6002", "Nissan", "e-NV200"),
    ("EV-FLEET-CSV-003", "CP-EVC-6003", "Mercedes", "eSprinter"),
    ("EV-FLEET-CSV-004", "SP-EVC-6004", "Maxus", "eDeliver 3"),
    ("EV-FLEET-CSV-005", "NW-EVC-6005", "Hyundai", "Kona Electric"),
    ("EV-FLEET-CSV-006", "EP-EVC-6006", "MG", "ZS EV"),
    ("EV-FLEET-CSV-007", "WP-EVC-6007", "Tesla", "Model Y"),
    ("EV-FLEET-CSV-008", "CP-EVC-6008", "Renault", "Kangoo E-Tech"),
]


def risk_level(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 40:
        return "high"
    if score >= 20:
        return "medium"
    return "low"


def status_from_risk(level: str) -> str:
    if level == "critical":
        return "critical"
    if level in {"high", "medium"}:
        return "warning"
    return "healthy"


def _series_mean(frame: pd.DataFrame, column: str, default: float = 0.0) -> float:
    if column not in frame:
        return default
    value = pd.to_numeric(frame[column], errors="coerce").dropna().mean()
    return default if pd.isna(value) else float(value)


def _series_max(frame: pd.DataFrame, column: str, default: float = 0.0) -> float:
    if column not in frame:
        return default
    value = pd.to_numeric(frame[column], errors="coerce").dropna().max()
    return default if pd.isna(value) else float(value)


def derive_part_scores(frame: pd.DataFrame) -> dict[str, float]:
    failure = _series_mean(frame, "Failure_Probability") * 100
    health_loss = max(0.0, (1 - _series_mean(frame, "Component_Health_Score", 0.85)) * 100)
    battery_temp = max(0.0, (_series_max(frame, "Battery_Temperature", 30) - 35) * 2)
    motor_temp = max(0.0, (_series_max(frame, "Motor_Temperature", 60) - 75) * 1.5)
    brake_wear = _series_mean(frame, "Brake_Pad_Wear") * 100
    tire_pressure_delta = abs(_series_mean(frame, "Tire_Pressure", 34) - 34) * 4
    suspension_load = max(0.0, (_series_mean(frame, "Suspension_Load", 80) - 120) * 0.5)
    return {
        "Battery Pack": min(max(failure, health_loss, battery_temp), 100),
        "Battery Cooling System": min(max(battery_temp, health_loss), 100),
        "Electric Motor": min(max(motor_temp, _series_max(frame, "Motor_Vibration", 1) * 25), 100),
        "Motor Controller": min(max(motor_temp * 0.8, failure), 100),
        "Brake Pads": min(max(brake_wear, failure), 100),
        "Tires": min(max(tire_pressure_delta, _series_max(frame, "Tire_Temperature", 30) - 35), 100),
        "Suspension System": min(max(suspension_load, failure), 100),
        "Charging Port": min(max(_series_mean(frame, "Charge_Cycles", 200) / 20, health_loss), 100),
        "Inverter": min(max(_series_mean(frame, "Power_Consumption", 20), failure), 100),
        "Thermal Management System": min(max(battery_temp, motor_temp), 100),
    }


async def seed_ev_csv_fleet_data() -> int:
    if not settings.mongodb_uri:
        print("MONGODB_URI is not configured. Create backend/.env before seeding EV CSV fleet data.")
        return 1
    if not CSV_PATH.exists():
        print(f"EV CSV dataset not found: {CSV_PATH}")
        return 1

    client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    try:
        db = client[settings.mongodb_db_name]
        await db.command("ping")
        admin_user = await db[USER_COLLECTION].find_one({"email": "admin@fleet.local"})
        if not admin_user:
            print("Admin demo user not found. Run: python scripts/seed_users.py")
            return 1

        df = pd.read_csv(CSV_PATH)
        if df.empty:
            print("EV CSV dataset is empty.")
            return 1
        groups = [group.copy() for _, group in df.groupby(df.index % len(CSV_VEHICLES))]

        vehicles = []
        for index, (code, reg, brand, model) in enumerate(CSV_VEHICLES):
            frame = groups[index]
            part_scores = derive_part_scores(frame)
            vehicle_score = max(part_scores.values())
            vehicle_health = status_from_risk(risk_level(vehicle_score))
            mileage = round(_series_max(frame, "Distance_Traveled", 0), 2)
            existing = await db[VEHICLE_COLLECTION].find_one({"vehicle_code": code})
            payload = {
                "vehicle_code": code,
                "registration_number": reg,
                "vehicle_type": "electric_van",
                "brand": brand,
                "model": model,
                "year": 2022 + (index % 3),
                "fuel_type": "electric",
                "current_mileage": mileage,
                "battery_capacity_kwh": 50 + index * 3,
                "status": "under_maintenance" if vehicle_health == "critical" else "active",
                "health_status": vehicle_health,
            }
            if existing:
                await db[VEHICLE_COLLECTION].update_one(
                    {"_id": existing["_id"]},
                    {"$set": {k: v for k, v in payload.items() if k not in ["vehicle_code", "registration_number"]}},
                )
                vehicle = await db[VEHICLE_COLLECTION].find_one({"_id": existing["_id"]})
                print(f"UPDATED CSV vehicle: {code}")
            else:
                result = await db[VEHICLE_COLLECTION].insert_one(build_vehicle_document(payload))
                vehicle = await db[VEHICLE_COLLECTION].find_one({"_id": result.inserted_id})
                print(f"CREATED CSV vehicle: {code}")
            vehicles.append((vehicle, part_scores, frame))

            existing_part_names = {
                part["part_name"]
                for part in await db[VEHICLE_PART_COLLECTION].find({"vehicle_id": vehicle["_id"]}).to_list(length=100)
            }
            for part_name, category in DEFAULT_EV_PARTS:
                score = round(part_scores.get(part_name, 0), 2)
                level = risk_level(score)
                part_payload = {
                    "part_name": part_name,
                    "part_category": category,
                    "risk_level": level,
                    "risk_score": score,
                    "status": status_from_risk(level),
                    "notes": "EV CSV seed data",
                }
                if part_name in existing_part_names:
                    await db[VEHICLE_PART_COLLECTION].update_one(
                        {"vehicle_id": vehicle["_id"], "part_name": part_name},
                        {"$set": {**part_payload, "updated_at": utc_now()}},
                    )
                else:
                    await db[VEHICLE_PART_COLLECTION].insert_one(build_vehicle_part_document(vehicle["_id"], part_payload))
            print(f"ENSURED CSV-derived part risk for: {code}")

        existing_records = await db[MAINTENANCE_COLLECTION].count_documents({"notes": "EV CSV seed data"})
        if existing_records == 0:
            for vehicle, part_scores, frame in vehicles:
                top_parts = sorted(part_scores.items(), key=lambda item: item[1], reverse=True)[:2]
                for part_name, score in top_parts:
                    part = await db[VEHICLE_PART_COLLECTION].find_one({"vehicle_id": vehicle["_id"], "part_name": part_name})
                    level = risk_level(score)
                    await db[MAINTENANCE_COLLECTION].insert_one(
                        build_maintenance_document(
                            {
                                "vehicle_id": vehicle["_id"],
                                "part_id": part["_id"] if part else None,
                                "part_name": part_name,
                                "maintenance_type": "predictive",
                                "issue_type": f"CSV-derived {level} risk pattern",
                                "service_date": utc_now(),
                                "mileage_at_service": vehicle["current_mileage"],
                                "technician_name": "CSV Seed Technician",
                                "service_center": "FleetOpt Demo Service Center",
                                "cost": 12000 + score * 150,
                                "status": "scheduled",
                                "priority": "critical" if level == "critical" else "high" if level == "high" else "medium",
                                "notes": "EV CSV seed data",
                            },
                            admin_user["_id"],
                        )
                    )
            print("CREATED CSV-derived maintenance records")
        else:
            print("SKIPPED CSV-derived maintenance records: already exists")

        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(seed_ev_csv_fleet_data()))
