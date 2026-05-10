from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.core.config import settings


mongo_client: Optional[AsyncIOMotorClient] = None
mongo_database: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> None:
    global mongo_client, mongo_database

    if not settings.mongodb_uri:
        mongo_client = None
        mongo_database = None
        return

    mongo_client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    mongo_database = mongo_client[settings.mongodb_db_name]


async def close_mongo_connection() -> None:
    global mongo_client, mongo_database

    if mongo_client is not None:
        mongo_client.close()

    mongo_client = None
    mongo_database = None


def get_database() -> Optional[AsyncIOMotorDatabase]:
    return mongo_database


async def ping_database() -> dict:
    if not settings.mongodb_uri:
        return {
            "configured": False,
            "connected": False,
            "status": "not_configured",
            "database": settings.mongodb_db_name,
        }

    if mongo_database is None:
        return {
            "configured": True,
            "connected": False,
            "status": "not_connected",
            "database": settings.mongodb_db_name,
        }

    try:
        await mongo_database.command("ping")
        return {
            "configured": True,
            "connected": True,
            "status": "connected",
            "database": settings.mongodb_db_name,
        }
    except PyMongoError as exc:
        return {
            "configured": True,
            "connected": False,
            "status": "connection_error",
            "database": settings.mongodb_db_name,
            "error": str(exc),
        }
