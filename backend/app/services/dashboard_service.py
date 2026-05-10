from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.maintenance_model import MAINTENANCE_COLLECTION
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.services.alert_service import get_active_alert_count
from app.services.demand_forecasting_service import get_demand_dashboard_summary
from app.services.maintenance_service import get_maintenance_summary
from app.services.predictive_maintenance_service import get_predictive_dashboard_metrics
from app.services.route_optimizer_service import get_route_dashboard_summary
from app.utils.object_id import serialize_mongo_list


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db


async def get_fleet_dashboard_summary() -> dict[str, Any]:
    db = _db()
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    summary = {
        "total_vehicles": await db[VEHICLE_COLLECTION].count_documents({}),
        "active_vehicles": await db[VEHICLE_COLLECTION].count_documents({"status": "active"}),
        "under_maintenance": await db[VEHICLE_COLLECTION].count_documents({"status": "under_maintenance"}),
        "critical_vehicles": await db[VEHICLE_COLLECTION].count_documents({"health_status": "critical"}),
        "active_alerts": await get_active_alert_count(),
        "upcoming_maintenance": await db[MAINTENANCE_COLLECTION].count_documents({"status": "scheduled"}),
        "completed_maintenance_this_month": await db[MAINTENANCE_COLLECTION].count_documents(
            {"status": "completed", "service_date": {"$gte": month_start}}
        ),
    }
    summary["predictive_maintenance"] = await get_predictive_dashboard_metrics()
    summary["demand_forecasting"] = await get_demand_dashboard_summary()
    summary["route_optimization"] = await get_route_dashboard_summary()
    return summary


async def get_vehicle_health_distribution() -> dict[str, int]:
    collection = _db()[VEHICLE_COLLECTION]
    return {
        "healthy": await collection.count_documents({"health_status": "healthy"}),
        "warning": await collection.count_documents({"health_status": "warning"}),
        "critical": await collection.count_documents({"health_status": "critical"}),
        "unknown": await collection.count_documents({"health_status": "unknown"}),
    }


async def get_maintenance_overview() -> dict[str, int]:
    return await get_maintenance_summary()


async def get_recent_alerts(limit: int = 10) -> list[dict[str, Any]]:
    limit = min(max(limit, 1), 50)
    cursor = _db()[ALERT_COLLECTION].find({}).sort("created_at", -1).limit(limit)
    return serialize_mongo_list(await cursor.to_list(length=limit))


async def get_upcoming_maintenance(limit: int = 10) -> list[dict[str, Any]]:
    limit = min(max(limit, 1), 50)
    cursor = (
        _db()[MAINTENANCE_COLLECTION]
        .find({"status": {"$in": ["scheduled", "in_progress"]}})
        .sort("service_date", 1)
        .limit(limit)
    )
    return serialize_mongo_list(await cursor.to_list(length=limit))
