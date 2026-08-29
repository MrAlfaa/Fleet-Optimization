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
DEMAND_ACTIVE_RUN_COLLECTION = "demand_active_run"
DEMAND_ACTIVE_RUN_POINTER_ID = "active"
OPERATIONAL_DEMAND_DAILY_COLLECTION = "operational_demand_daily"

DEMAND_LEVELS = {"low", "medium", "high", "very_high"}
DEMAND_MODEL_TYPES = {"baseline_prophet", "graph_enhanced_prophet"}
DEMAND_RUN_TYPES = {"artifact_import", "model_forecast", "manual_refresh"}
DEMAND_REFRESH_SOURCES = {"artifact", "model"}
DEMAND_RUN_STATUSES = {"staging", "completed", "failed", "partial"}


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
        "model_version": data.get("model_version"),
        "lower_bound": data.get("lower_bound"),
        "upper_bound": data.get("upper_bound"),
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
        "model_run_id": data.get("model_run_id"),
        "model_version": data.get("model_version"),
        "created_at": data.get("created_at", utc_now()),
    }


def build_demand_model_run_document(data: dict[str, Any]) -> dict[str, Any]:
    generated_at = data.get("generated_at") or data.get("created_at") or utc_now()
    return {
        "run_type": data["run_type"],
        "model_name": data["model_name"],
        "model_version": data.get("model_version") or data["model_name"],
        "artifact_source": data["artifact_source"],
        "metrics_snapshot": data.get("metrics_snapshot", {}),
        "forecast_start_date": data.get("forecast_start_date"),
        "forecast_end_date": data.get("forecast_end_date"),
        "zones_count": int(data.get("zones_count", 0)),
        "records_generated": int(data.get("records_generated", 0)),
        "status": data.get("status", "completed"),
        "request_fingerprint": data.get("request_fingerprint"),
        "horizon_days": int(data.get("horizon_days", 0)),
        "source_requested": data.get("source_requested"),
        "effective_source": data.get("effective_source") or data.get("source_requested"),
        "fallback_used": bool(data.get("fallback_used", False)),
        "validation": data.get("validation", {}),
        "activated_at": data.get("activated_at"),
        "generated_at": generated_at,
        "created_at": generated_at,
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
        # Legacy indexes excluded model_run_id and prevented preserving multiple runs.
        for collection_name, index_name in (
            (DEMAND_FORECAST_COLLECTION, "unique_demand_forecast_zone_date_model"),
            (FLEET_RECOMMENDATION_COLLECTION, "unique_fleet_recommendation_zone_date"),
        ):
            try:
                await db[collection_name].drop_index(index_name)
            except PyMongoError:
                pass
        await db[DEMAND_FORECAST_COLLECTION].create_index(
            [("model_run_id", ASCENDING), ("zone_id", ASCENDING), ("forecast_date", ASCENDING), ("model_type", ASCENDING)],
            unique=True,
            name="unique_demand_forecast_run_zone_date_model",
        )
        await db[DEMAND_FORECAST_COLLECTION].create_index([("forecast_date", ASCENDING)], name="demand_forecast_date")
        await db[DEMAND_FORECAST_COLLECTION].create_index([("predicted_demand", DESCENDING)], name="demand_forecast_value")
        await db[FLEET_RECOMMENDATION_COLLECTION].create_index(
            [("model_run_id", ASCENDING), ("zone_id", ASCENDING), ("forecast_date", ASCENDING)],
            unique=True,
            name="unique_fleet_recommendation_run_zone_date",
        )
        await db[FLEET_RECOMMENDATION_COLLECTION].create_index([("demand_level", ASCENDING)], name="fleet_recommendation_level")
        await db[DEMAND_MODEL_RUN_COLLECTION].create_index([("created_at", DESCENDING)], name="demand_model_run_created_at")
        await db[DEMAND_MODEL_RUN_COLLECTION].create_index(
            [("request_fingerprint", ASCENDING), ("status", ASCENDING)],
            name="demand_model_run_request_status",
        )
        await db[DEMAND_MODEL_RUN_COLLECTION].create_index(
            [("request_fingerprint", ASCENDING)],
            unique=True,
            partialFilterExpression={"status": "staging", "request_fingerprint": {"$type": "string"}},
            name="unique_staging_demand_request",
        )
        await db[DEMAND_ACTIVE_RUN_COLLECTION].create_index([("model_run_id", ASCENDING)], name="active_demand_model_run")
        await db[OPERATIONAL_DEMAND_DAILY_COLLECTION].create_index(
            [("operational_zone_id", ASCENDING), ("demand_date", ASCENDING)],
            unique=True,
            name="unique_operational_zone_demand_date",
        )
        await db[OPERATIONAL_DEMAND_DAILY_COLLECTION].create_index([("demand_date", DESCENDING)], name="operational_demand_date")
    except PyMongoError:
        return
