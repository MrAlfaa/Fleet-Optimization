import asyncio
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.core.security import hash_password
from app.models.user_model import USER_COLLECTION, USER_EMAIL_INDEX, build_user_document


DEMO_USERS = [
    {
        "full_name": "Admin User",
        "email": "admin@fleet.local",
        "password": "Admin@12345",
        "role": "admin",
    },
    {
        "full_name": "Fleet Manager",
        "email": "fleet.manager@fleet.local",
        "password": "Fleet@12345",
        "role": "fleet_manager",
    },
    {
        "full_name": "Maintenance Manager",
        "email": "maintenance.manager@fleet.local",
        "password": "Maint@12345",
        "role": "maintenance_manager",
    },
    {
        "full_name": "Route Planner",
        "email": "route.planner@fleet.local",
        "password": "Route@12345",
        "role": "route_planner",
    },
    {
        "full_name": "Driver User",
        "email": "driver@fleet.local",
        "password": "Driver@12345",
        "role": "driver",
    },
]


async def seed_users() -> int:
    if not settings.mongodb_uri:
        print("MONGODB_URI is not configured. Create backend/.env before seeding users.")
        return 1

    client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    try:
        db = client[settings.mongodb_db_name]
        await db.command("ping")
        collection = db[USER_COLLECTION]
        await collection.create_index([("email", ASCENDING)], unique=True, name=USER_EMAIL_INDEX)

        for user in DEMO_USERS:
            existing = await collection.find_one({"email": user["email"]})
            if existing:
                print(f"SKIPPED existing user: {user['email']}")
                continue

            document = build_user_document(user, hash_password(user["password"]))
            document["is_verified"] = True
            await collection.insert_one(document)
            print(f"CREATED user: {user['email']} ({user['role']})")

        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(seed_users()))
