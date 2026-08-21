from typing import Any

from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.user_model import USER_COLLECTION, utc_now


OPERATIONAL_COLLECTIONS = (
    "vehicles",
    "vehicle_parts",
    "maintenance_records",
    "maintenance_predictions",
    "alerts",
    "demand_zones",
    "demand_forecasts",
    "fleet_planning_recommendations",
    "demand_model_runs",
    "delivery_orders",
    "delivery_attempts",
    "route_plans",
    "route_segments",
    "route_model_runs",
    "driver_devices",
    "driver_issue_reports",
    "driver_trip_sessions",
    "driver_locations",
    "trip_events",
)


def retained_user_filter(admin_email: str) -> dict[str, Any]:
    return {"email": {"$ne": admin_email.strip().lower()}}


async def preview_demo_reset(admin_email: str) -> dict[str, Any]:
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not connected")
    email = admin_email.strip().lower()
    retained = await db[USER_COLLECTION].find_one({"email": email, "role": "admin"}, {"email": 1, "role": 1})
    if retained is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Retained admin account not found: {email}")
    counts = {name: await db[name].count_documents({}) for name in OPERATIONAL_COLLECTIONS}
    counts["users_to_remove"] = await db[USER_COLLECTION].count_documents(retained_user_filter(email))
    return {"retained_admin": email, "records_to_remove": counts}


async def reset_demo_data(admin_email: str) -> dict[str, Any]:
    preview = await preview_demo_reset(admin_email)
    db = get_database()
    deleted: dict[str, int] = {}
    for collection_name in OPERATIONAL_COLLECTIONS:
        result = await db[collection_name].delete_many({})
        deleted[collection_name] = result.deleted_count
    user_result = await db[USER_COLLECTION].delete_many(retained_user_filter(admin_email))
    deleted["users"] = user_result.deleted_count
    await db[USER_COLLECTION].update_one(
        {"email": admin_email.strip().lower()},
        {"$set": {"role": "admin", "is_active": True, "is_verified": True, "permission_overrides": {"deny": []}, "updated_at": utc_now()}},
    )
    return {**preview, "deleted": deleted}
