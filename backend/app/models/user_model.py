from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.utils.object_id import serialize_mongo_document


USER_COLLECTION = "users"

USER_ROLES = {
    "admin",
    "fleet_manager",
    "maintenance_manager",
    "route_planner",
    "driver",
}

USER_EMAIL_INDEX = "unique_user_email"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_user_document(data: dict[str, Any], password_hash: str) -> dict[str, Any]:
    now = utc_now()
    return {
        "full_name": data["full_name"],
        "email": data["email"].lower(),
        "password_hash": password_hash,
        "role": data["role"],
        "phone": data.get("phone"),
        "is_active": data.get("is_active", True),
        "is_verified": data.get("is_verified", True),
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
    }


def safe_user_document(user: dict[str, Any] | None) -> dict[str, Any] | None:
    if user is None:
        return None
    serialized = serialize_mongo_document(user)
    serialized.pop("password_hash", None)
    return serialized


async def ensure_user_indexes() -> None:
    db = get_database()
    if db is None:
        return

    try:
        await db[USER_COLLECTION].create_index(
            [("email", ASCENDING)],
            unique=True,
            name=USER_EMAIL_INDEX,
        )
    except PyMongoError:
        # Startup should not fail because Atlas is temporarily unavailable.
        return
