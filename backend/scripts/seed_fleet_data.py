import asyncio
import sys
from datetime import timedelta
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.models.alert_model import ALERT_COLLECTION, build_alert_document
from app.models.maintenance_model import MAINTENANCE_COLLECTION, build_maintenance_document
from app.models.user_model import USER_COLLECTION, utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION, build_vehicle_document
from app.models.vehicle_part_model import DEFAULT_EV_PARTS, VEHICLE_PART_COLLECTION, build_vehicle_part_document


DEMO_VEHICLES = [
    ("EV-FLEET-001", "WP-EV-1001", "BYD", "T3", 2022, 45000, 50, "healthy"),
    ("EV-FLEET-002", "WP-EV-1002", "Nissan", "e-NV200", 2021, 62000, 40, "warning"),
    ("EV-FLEET-003", "WP-EV-1003", "Mercedes", "eSprinter", 2023, 28500, 55, "healthy"),
    ("EV-FLEET-004", "CP-EV-2004", "Maxus", "eDeliver 3", 2022, 50800, 52, "critical"),
    ("EV-FLEET-005", "SP-EV-3005", "BYD", "M3", 2020, 77000, 44, "warning"),
    ("EV-FLEET-006", "WP-EV-1006", "Hyundai", "Kona Electric", 2023, 22000, 64, "healthy"),
    ("EV-FLEET-007", "NW-EV-4007", "MG", "ZS EV", 2022, 39000, 50, "unknown"),
    ("EV-FLEET-008", "EP-EV-5008", "Tesla", "Model Y", 2023, 18000, 75, "healthy"),
]


async def seed_fleet_data() -> int:
    if not settings.mongodb_uri:
        print("MONGODB_URI is not configured. Create backend/.env before seeding fleet data.")
        return 1

    client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    try:
        db = client[settings.mongodb_db_name]
        await db.command("ping")

        admin_user = await db[USER_COLLECTION].find_one({"email": "admin@fleet.local"})
        if not admin_user:
            print("Admin demo user not found. Run: python scripts/seed_users.py")
            return 1

        vehicles_by_code = {}
        for code, reg, brand, model, year, mileage, capacity, health in DEMO_VEHICLES:
            existing = await db[VEHICLE_COLLECTION].find_one({"vehicle_code": code})
            if existing:
                print(f"SKIPPED existing vehicle: {code}")
                vehicles_by_code[code] = existing
                continue

            document = build_vehicle_document(
                {
                    "vehicle_code": code,
                    "registration_number": reg,
                    "vehicle_type": "electric_van",
                    "brand": brand,
                    "model": model,
                    "year": year,
                    "fuel_type": "electric",
                    "current_mileage": mileage,
                    "battery_capacity_kwh": capacity,
                    "status": "under_maintenance" if health == "critical" else "active",
                    "health_status": health,
                }
            )
            result = await db[VEHICLE_COLLECTION].insert_one(document)
            created = await db[VEHICLE_COLLECTION].find_one({"_id": result.inserted_id})
            vehicles_by_code[code] = created
            print(f"CREATED vehicle: {code}")

        for vehicle in vehicles_by_code.values():
            existing_part_names = {
                part["part_name"]
                for part in await db[VEHICLE_PART_COLLECTION].find({"vehicle_id": vehicle["_id"]}).to_list(length=100)
            }
            for part_name, part_category in DEFAULT_EV_PARTS:
                if part_name in existing_part_names:
                    continue
                risk_level = "critical" if vehicle["health_status"] == "critical" and part_name == "Battery Pack" else "unknown"
                status_value = "critical" if risk_level == "critical" else "unknown"
                await db[VEHICLE_PART_COLLECTION].insert_one(
                    build_vehicle_part_document(
                        vehicle["_id"],
                        {
                            "part_name": part_name,
                            "part_category": part_category,
                            "risk_level": risk_level,
                            "risk_score": 88 if risk_level == "critical" else 0,
                            "status": status_value,
                        },
                    )
                )
            print(f"ENSURED default parts for: {vehicle['vehicle_code']}")

        seeded_maintenance_count = await db[MAINTENANCE_COLLECTION].count_documents({"notes": "Seed data"})
        if seeded_maintenance_count == 0:
            vehicle_values = list(vehicles_by_code.values())
            for index in range(15):
                vehicle = vehicle_values[index % len(vehicle_values)]
                part = await db[VEHICLE_PART_COLLECTION].find_one({"vehicle_id": vehicle["_id"]})
                priority = ["low", "medium", "high", "critical"][index % 4]
                status_value = ["scheduled", "in_progress", "completed"][index % 3]
                service_date = utc_now() + timedelta(days=index - 5)
                record = build_maintenance_document(
                    {
                        "vehicle_id": vehicle["_id"],
                        "part_id": part["_id"] if part else None,
                        "part_name": part["part_name"] if part else "General Inspection",
                        "maintenance_type": ["preventive", "inspection", "replacement"][index % 3],
                        "issue_type": "Demo maintenance issue",
                        "service_date": service_date,
                        "mileage_at_service": vehicle["current_mileage"] + index * 250,
                        "technician_name": "Fleet Technician",
                        "service_center": "Colombo EV Service Center",
                        "cost": 15000 + index * 1250,
                        "status": status_value,
                        "priority": priority,
                        "notes": "Seed data",
                    },
                    admin_user["_id"],
                )
                await db[MAINTENANCE_COLLECTION].insert_one(record)
            print("CREATED 15 maintenance records")
        else:
            print("SKIPPED maintenance records: seed data already exists")

        seeded_alert_count = await db[ALERT_COLLECTION].count_documents({"message": {"$regex": "Seed data"}})
        if seeded_alert_count == 0:
            vehicle_values = list(vehicles_by_code.values())
            for index in range(8):
                vehicle = vehicle_values[index % len(vehicle_values)]
                severity = ["info", "warning", "high", "critical"][index % 4]
                await db[ALERT_COLLECTION].insert_one(
                    build_alert_document(
                        {
                            "alert_type": "maintenance",
                            "severity": severity,
                            "title": f"{severity.title()} Fleet Alert",
                            "message": f"Seed data alert for {vehicle['vehicle_code']}",
                            "linked_vehicle_id": vehicle["_id"],
                            "status": "active",
                            "created_by_system": True,
                        }
                    )
                )
            print("CREATED 8 alerts")
        else:
            print("SKIPPED alerts: seed data already exists")

        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(seed_fleet_data()))
