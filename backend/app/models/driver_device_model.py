from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database


DRIVER_DEVICE_COLLECTION = "driver_devices"


async def ensure_driver_device_indexes() -> None:
    db = get_database()
    if db is None:
        return
    try:
        collection = db[DRIVER_DEVICE_COLLECTION]
        await collection.create_index([("user_id", ASCENDING)], name="driver_device_user")
        await collection.create_index([("installation_id_hash", ASCENDING)], name="driver_device_installation")
        await collection.create_index([("status", ASCENDING), ("last_seen_at", DESCENDING)], name="driver_device_status")
        await collection.create_index(
            [("user_id", ASCENDING), ("active_slot", ASCENDING)],
            unique=True,
            sparse=True,
            name="one_active_device_per_driver",
        )
    except PyMongoError:
        return
