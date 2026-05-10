from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document


DEMAND_ZONE_COLLECTION = "demand_zones"
DEMAND_FORECAST_COLLECTION = "demand_forecasts"
FLEET_RECOMMENDATION_COLLECTION = "fleet_planning_recommendations"
DEMAND_MODEL_RUN_COLLECTION = "demand_model_runs"

DEMAND_LEVELS = {"low", "medium", "high", "very_high"}
DEMAND_MODEL_TYPES = {"baseline_prophet", "graph_enhanced_prophet"}
DEMAND_RUN_TYPES = {"artifact_import", "model_forecast", "manual_refresh"}
DEMAND_REFRESH_SOURCES = {"artifact", "model"}
DEMAND_RUN_STATUSES = {"completed", "failed", "partial"}


def build_demand_zone_document(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "zone_id": data["zone_id"],
        "zone_name": data.get("zone_name"),
        "city": data.get("city"),
        "state": data.get("state"),
        "zone_lat": data.get("zone_lat"),
        "zone_lng": data.get("zone_lng"),
        "customer_count": data.get("customer_count"),
        "is_active": data.get("is_active", True),
        "created_at": data.get("created_at", now),
        "updated_at": now,
    }


def build_demand_forecast_document(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "zone_id": data["zone_id"],
        "forecast_date": data["forecast_date"],
        "baseline_prophet_forecast": data.get("baseline_prophet_forecast"),
        "graph_enhanced_forecast": data["graph_enhanced_forecast"],
        "predicted_demand": data["predicted_demand"],
        "forecast_horizon_days": data.get("forecast_horizon_days"),
        "model_type": data.get("model_type", "graph_enhanced_prophet"),
        "model_run_id": data.get("model_run_id"),
        "created_at": data.get("created_at", utc_now()),
    }


def build_fleet_recommendation_document(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "zone_id": data["zone_id"],
        "forecast_date": data["forecast_date"],
        "predicted_demand": data["predicted_demand"],
        "demand_level": data["demand_level"],
        "estimated_required_vehicles": data["estimated_required_vehicles"],
        "recommended_action": data["recommended_action"],
        "created_at": data.get("created_at", utc_now()),
    }


def build_demand_model_run_document(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_type": data["run_type"],
        "model_name": data["model_name"],
        "artifact_source": data["artifact_source"],
        "metrics_snapshot": data.get("metrics_snapshot", {}),
        "forecast_start_date": data.get("forecast_start_date"),
        "forecast_end_date": data.get("forecast_end_date"),
        "zones_count": int(data.get("zones_count", 0)),
        "records_generated": int(data.get("records_generated", 0)),
        "status": data.get("status", "completed"),
        "created_at": data.get("created_at", utc_now()),
        "created_by": data.get("created_by"),
    }


def safe_demand_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    return serialize_mongo_document(document)


async def ensure_demand_indexes() -> None:
    db = get_database()
    if db is None:
        return

    try:
        await db[DEMAND_ZONE_COLLECTION].create_index([("zone_id", ASCENDING)], unique=True, name="unique_demand_zone_id")
        await db[DEMAND_ZONE_COLLECTION].create_index([("is_active", ASCENDING)], name="demand_zone_active")
        await db[DEMAND_FORECAST_COLLECTION].create_index(
            [("zone_id", ASCENDING), ("forecast_date", ASCENDING), ("model_type", ASCENDING)],
            unique=True,
            name="unique_demand_forecast_zone_date_model",
        )
        await db[DEMAND_FORECAST_COLLECTION].create_index([("forecast_date", ASCENDING)], name="demand_forecast_date")
        await db[DEMAND_FORECAST_COLLECTION].create_index([("predicted_demand", DESCENDING)], name="demand_forecast_value")
        await db[FLEET_RECOMMENDATION_COLLECTION].create_index(
            [("zone_id", ASCENDING), ("forecast_date", ASCENDING)],
            unique=True,
            name="unique_fleet_recommendation_zone_date",
        )
        await db[FLEET_RECOMMENDATION_COLLECTION].create_index([("demand_level", ASCENDING)], name="fleet_recommendation_level")
        await db[DEMAND_MODEL_RUN_COLLECTION].create_index([("created_at", DESCENDING)], name="demand_model_run_created_at")
    except PyMongoError:
        return
