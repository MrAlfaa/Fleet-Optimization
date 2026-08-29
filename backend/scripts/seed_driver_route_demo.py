import asyncio
import sys
from datetime import timedelta
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.models.delivery_model import DELIVERY_COLLECTION, build_delivery_order_document
from app.models.driver_execution_model import DELIVERY_ATTEMPT_COLLECTION, VEHICLE_TRIP_INSPECTION_COLLECTION
from app.models.inspection_model import INSPECTION_COLLECTION, build_inspection_document
from app.models.maintenance_model import MAINTENANCE_COLLECTION, build_maintenance_document
from app.models.route_model import ROUTE_PLAN_COLLECTION, ROUTE_SEGMENT_COLLECTION, build_route_plan_document, build_route_segment_document
from app.models.trip_model import DRIVER_LOCATION_COLLECTION, TRIP_EVENT_COLLECTION, TRIP_SESSION_COLLECTION
from app.models.user_model import USER_COLLECTION, utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION, build_vehicle_document
from app.models.vehicle_part_model import DEFAULT_EV_PARTS, VEHICLE_PART_COLLECTION, build_vehicle_part_document
from app.utils.geo_utils import haversine_distance_km
from app.utils.route_utils import format_optimized_stop_order


DRIVER_EMAIL = "driver@fleet.local"
ADMIN_EMAIL = "admin@fleet.local"
VEHICLE_CODE = "EV-FLEET-LIVE-001"
ROUTE_CODE = "ROUTE-LIVE-DEMO-001"

DEMO_ORDERS = [
    {
        "order_code": "LIVE-DEMO-ORD-001",
        "customer_name": "Colombo Central Customer",
        "pickup_latitude": 6.9271,
        "pickup_longitude": 79.8612,
        "drop_latitude": 6.9147,
        "drop_longitude": 79.8729,
        "pickup_address": "Colombo Depot",
        "drop_address": "No. 24 Union Place, Colombo",
        "zone_id": "LK_colombo_central",
        "priority": "high",
        "parcel_weight": 12.5,
        "load_profile": {"length_cm": 60, "width_cm": 40, "height_cm": 35, "fragile": True, "do_not_tilt": True},
    },
    {
        "order_code": "LIVE-DEMO-ORD-002",
        "customer_name": "Nugegoda Retail Stop",
        "pickup_latitude": 6.9271,
        "pickup_longitude": 79.8612,
        "drop_latitude": 6.8649,
        "drop_longitude": 79.8997,
        "pickup_address": "Colombo Depot",
        "drop_address": "High Level Road, Nugegoda",
        "zone_id": "LK_nugegoda",
        "priority": "medium",
        "parcel_weight": 8.0,
        "load_profile": {"length_cm": 45, "width_cm": 35, "height_cm": 30, "fragile": False},
    },
    {
        "order_code": "LIVE-DEMO-ORD-003",
        "customer_name": "Malabe Fulfillment Stop",
        "pickup_latitude": 6.9271,
        "pickup_longitude": 79.8612,
        "drop_latitude": 6.9061,
        "drop_longitude": 79.9696,
        "pickup_address": "Colombo Depot",
        "drop_address": "IT Park Avenue, Malabe",
        "zone_id": "LK_malabe",
        "priority": "urgent",
        "parcel_weight": 18.0,
        "load_profile": {"length_cm": 70, "width_cm": 50, "height_cm": 45, "fragile": True, "two_person_lift": True},
    },
]


async def upsert_vehicle(db, driver_id):
    vehicle = await db[VEHICLE_COLLECTION].find_one({"vehicle_code": VEHICLE_CODE})
    data = {
        "vehicle_code": VEHICLE_CODE,
        "registration_number": "LIVE-0901",
        "vehicle_type": "electric_van",
        "vehicle_category": "van",
        "brand": "Demo EV",
        "model": "Driver Live Van",
        "year": 2025,
        "in_service_date": utc_now() - timedelta(days=540),
        "payload_capacity_kg": 1200,
        "onboarding_type": "existing_fleet",
        "commissioning_status": "passed",
        "fuel_type": "electric",
        "current_mileage": 42800,
        "battery_capacity_kwh": 82,
        "assigned_driver_id": driver_id,
        "status": "active",
        "health_status": "healthy",
    }
    if vehicle is None:
        document = build_vehicle_document(data)
        result = await db[VEHICLE_COLLECTION].insert_one(document)
        vehicle = await db[VEHICLE_COLLECTION].find_one({"_id": result.inserted_id})
        print(f"CREATED vehicle: {VEHICLE_CODE}")
    else:
        await db[VEHICLE_COLLECTION].update_one(
            {"_id": vehicle["_id"]},
            {"$set": {**data, "updated_at": utc_now()}},
        )
        vehicle = await db[VEHICLE_COLLECTION].find_one({"_id": vehicle["_id"]})
        print(f"UPDATED vehicle: {VEHICLE_CODE}")

    existing_parts = await db[VEHICLE_PART_COLLECTION].count_documents({"vehicle_id": vehicle["_id"]})
    if existing_parts == 0:
        await db[VEHICLE_PART_COLLECTION].insert_many(
            [
                build_vehicle_part_document(
                    vehicle["_id"],
                    {
                        "part_name": part_name,
                        "part_category": category,
                        "risk_level": "low",
                        "risk_score": 0,
                        "status": "healthy",
                    },
                )
                for part_name, category in DEFAULT_EV_PARTS
            ]
        )
        print(f"CREATED default EV parts for: {VEHICLE_CODE}")
    return vehicle


async def upsert_assessment_evidence(db, vehicle, admin_id):
    now = utc_now()
    import_batch_id = "driver-route-demo-history"
    maintenance_data = {
        "vehicle_id": vehicle["_id"],
        "part_name": "Brake and tire service",
        "maintenance_type": "preventive",
        "maintenance_system": "braking",
        "event_kind": "scheduled_service",
        "issue_type": "Routine service",
        "service_date": now - timedelta(days=90),
        "mileage_at_service": 41000,
        "technician_name": "Demo Technician",
        "service_center": "Colombo Fleet Workshop",
        "status": "completed",
        "priority": "medium",
        "notes": "Imported baseline service history for the repeatable driver QA route.",
        "record_source": "imported_history",
        "import_batch_id": import_batch_id,
        "work_order_status": "completed",
        "completed_by": admin_id,
        "completed_at": now - timedelta(days=90),
    }
    maintenance = build_maintenance_document(maintenance_data, admin_id)
    await db[MAINTENANCE_COLLECTION].update_one(
        {"vehicle_id": vehicle["_id"], "import_batch_id": import_batch_id},
        {"$set": maintenance},
        upsert=True,
    )

    commissioning = build_inspection_document(
        {
            "vehicle_id": vehicle["_id"],
            "inspection_type": "commissioning",
            "feature_hash": f"commissioning:{vehicle['_id']}",
            "priority": "medium",
            "inspection_areas": ["vehicle_profile", "roadworthiness"],
            "notes": "Approved commissioning evidence for the repeatable driver QA route.",
        },
        admin_id,
        now=now - timedelta(days=100),
    )
    commissioning.update({
        "status": "returned_to_service",
        "is_active": False,
        "decision": "returned_to_service",
        "decided_by": admin_id,
        "decided_at": now - timedelta(days=100),
        "updated_at": now - timedelta(days=100),
    })
    await db[INSPECTION_COLLECTION].update_one(
        {"vehicle_id": vehicle["_id"], "inspection_type": "commissioning"},
        {"$set": commissioning},
        upsert=True,
    )


async def upsert_orders(db, vehicle_id, driver_id):
    order_ids = []
    for order in DEMO_ORDERS:
        existing = await db[DELIVERY_COLLECTION].find_one({"order_code": order["order_code"]})
        data = {
            **order,
            "is_demo": True,
            "delivery_date": utc_now().date().isoformat(),
            "delivery_period": "second_half",
            "delivery_status": "in_route",
            "assigned_vehicle_id": vehicle_id,
            "assigned_driver_id": driver_id,
        }
        if existing is None:
            document = build_delivery_order_document(data)
            result = await db[DELIVERY_COLLECTION].insert_one(document)
            existing = await db[DELIVERY_COLLECTION].find_one({"_id": result.inserted_id})
            print(f"CREATED delivery: {order['order_code']}")
        else:
            await db[DELIVERY_COLLECTION].update_one(
                {"_id": existing["_id"]},
                {"$set": {**data, "updated_at": utc_now()}},
            )
            existing = await db[DELIVERY_COLLECTION].find_one({"_id": existing["_id"]})
            print(f"UPDATED delivery: {order['order_code']}")
        order_ids.append(existing["_id"])
    return order_ids


async def upsert_route(db, vehicle_id, driver_id, order_ids, admin_id):
    existing = await db[ROUTE_PLAN_COLLECTION].find_one({"route_code": ROUTE_CODE})
    if existing is not None:
        route_filter = {"route_id": existing["_id"]}
        sessions = await db[TRIP_SESSION_COLLECTION].find(route_filter, {"_id": 1}).to_list(length=100)
        session_ids = [row["_id"] for row in sessions]
        await db[TRIP_EVENT_COLLECTION].delete_many(route_filter)
        await db[DRIVER_LOCATION_COLLECTION].delete_many(route_filter)
        await db[VEHICLE_TRIP_INSPECTION_COLLECTION].delete_many(route_filter)
        await db[DELIVERY_ATTEMPT_COLLECTION].delete_many({"route_id": existing["_id"]})
        if session_ids:
            await db[TRIP_SESSION_COLLECTION].delete_many({"_id": {"$in": session_ids}})
    route_points = [
        {
            "type": "depot",
            "order_id": None,
            "order_code": "DEPOT",
            "latitude": 6.9271,
            "longitude": 79.8612,
        },
        *[
            {
                "type": "delivery",
                "order_id": str(order_id),
                "order_code": order["order_code"],
                "latitude": order["drop_latitude"],
                "longitude": order["drop_longitude"],
                "zone_id": order["zone_id"],
                "priority": order["priority"],
            }
            for order_id, order in zip(order_ids, DEMO_ORDERS, strict=True)
        ],
    ]
    data = {
        "route_code": ROUTE_CODE,
        "route_name": "Live Driver Demo Route",
        "vehicle_id": vehicle_id,
        "driver_id": driver_id,
        "depot_latitude": 6.9271,
        "depot_longitude": 79.8612,
        "depot_name": "Colombo Depot",
        "delivery_order_ids": order_ids,
        "optimized_stop_order": format_optimized_stop_order(route_points, [0, 1, 2, 3, 0]),
        "total_predicted_eta_minutes": 72,
        "total_route_cost_score": 88,
        "average_delay_probability": 0.24,
        "optimization_method": "Seeded live trip demo route",
        "status": "dispatched",
        "delivery_date": utc_now().date().isoformat(),
        "delivery_period": "second_half",
        "created_by": admin_id,
        "dispatched_at": utc_now(),
    }
    if existing is None:
        document = build_route_plan_document(data)
        result = await db[ROUTE_PLAN_COLLECTION].insert_one(document)
        route = await db[ROUTE_PLAN_COLLECTION].find_one({"_id": result.inserted_id})
        print(f"CREATED route: {ROUTE_CODE}")
    else:
        await db[ROUTE_PLAN_COLLECTION].update_one(
            {"_id": existing["_id"]},
            {"$set": {**data, "updated_at": utc_now()}},
        )
        route = await db[ROUTE_PLAN_COLLECTION].find_one({"_id": existing["_id"]})
        print(f"UPDATED route: {ROUTE_CODE}")

    await db[ROUTE_SEGMENT_COLLECTION].delete_many({"route_plan_id": route["_id"]})
    points = [(6.9271, 79.8612)]
    for order in DEMO_ORDERS:
        points.append((order["drop_latitude"], order["drop_longitude"]))
    points.append((6.9271, 79.8612))
    segment_documents = []
    for index in range(len(points) - 1):
        from_lat, from_lng = points[index]
        to_lat, to_lng = points[index + 1]
        distance = haversine_distance_km(from_lat, from_lng, to_lat, to_lng)
        segment_documents.append(
            build_route_segment_document(
                {
                    "route_plan_id": route["_id"],
                    "from_stop_index": index,
                    "to_stop_index": index + 1,
                    "from_latitude": from_lat,
                    "from_longitude": from_lng,
                    "to_latitude": to_lat,
                    "to_longitude": to_lng,
                    "distance_km": distance,
                    "predicted_eta_minutes": max(distance * 3.5, 8),
                    "delay_probability": 0.24,
                    "delay_prediction": 0,
                    "delay_risk_level": "low",
                    "route_cost_score": max(distance * 3.5, 8) * 1.072,
                }
            )
        )
    await db[ROUTE_SEGMENT_COLLECTION].insert_many(segment_documents)
    print(f"REFRESHED route segments: {ROUTE_CODE}")
    return route


async def seed_driver_route_demo() -> int:
    if not settings.mongodb_uri:
        print("MONGODB_URI is not configured. Create backend/.env before seeding demo route.")
        return 1

    client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    try:
        db = client[settings.mongodb_db_name]
        await db.command("ping")
        await db[DELIVERY_COLLECTION].create_index([("order_code", ASCENDING)], unique=True, name="unique_delivery_order_code")
        await db[ROUTE_PLAN_COLLECTION].create_index([("route_code", ASCENDING)], unique=True, name="unique_route_code")
        await db[VEHICLE_COLLECTION].create_index([("vehicle_code", ASCENDING)], unique=True, name="unique_vehicle_code")

        driver = await db[USER_COLLECTION].find_one({"email": DRIVER_EMAIL})
        admin = await db[USER_COLLECTION].find_one({"email": ADMIN_EMAIL})
        if driver is None or admin is None:
            print("Demo users are missing. Run: python scripts/seed_users.py")
            return 1

        vehicle = await upsert_vehicle(db, driver["_id"])
        await upsert_assessment_evidence(db, vehicle, admin["_id"])
        order_ids = await upsert_orders(db, vehicle["_id"], driver["_id"])
        await upsert_route(db, vehicle["_id"], driver["_id"], order_ids, admin["_id"])
        print("Driver route demo seed completed.")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(seed_driver_route_demo()))
