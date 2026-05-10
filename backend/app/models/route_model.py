from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document
from app.utils.route_utils import ROUTE_STATUSES, generate_route_code


ROUTE_PLAN_COLLECTION = "route_plans"
ROUTE_SEGMENT_COLLECTION = "route_segments"
ROUTE_MODEL_RUN_COLLECTION = "route_model_runs"


def build_route_plan_document(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "route_code": data.get("route_code") or generate_route_code(),
        "route_name": data.get("route_name"),
        "vehicle_id": data.get("vehicle_id"),
        "driver_id": data.get("driver_id"),
        "depot_latitude": float(data["depot_latitude"]),
        "depot_longitude": float(data["depot_longitude"]),
        "depot_name": data.get("depot_name"),
        "delivery_order_ids": data.get("delivery_order_ids", []),
        "optimized_stop_order": data.get("optimized_stop_order", []),
        "total_predicted_eta_minutes": float(data.get("total_predicted_eta_minutes", 0)),
        "total_route_cost_score": float(data.get("total_route_cost_score", 0)),
        "average_delay_probability": float(data.get("average_delay_probability", 0)),
        "optimization_method": data.get("optimization_method", "distance-based OR-Tools single vehicle"),
        "status": data.get("status", "optimized"),
        "demand_context": data.get("demand_context"),
        "maintenance_context": data.get("maintenance_context"),
        "created_by": data.get("created_by"),
        "created_at": now,
        "updated_at": now,
        "dispatched_at": data.get("dispatched_at"),
        "completed_at": data.get("completed_at"),
    }


def build_route_segment_document(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "route_plan_id": data["route_plan_id"],
        "from_stop_index": int(data["from_stop_index"]),
        "to_stop_index": int(data["to_stop_index"]),
        "from_latitude": float(data["from_latitude"]),
        "from_longitude": float(data["from_longitude"]),
        "to_latitude": float(data["to_latitude"]),
        "to_longitude": float(data["to_longitude"]),
        "distance_km": float(data["distance_km"]),
        "predicted_eta_minutes": float(data["predicted_eta_minutes"]),
        "delay_probability": float(data["delay_probability"]),
        "delay_prediction": int(data["delay_prediction"]),
        "delay_risk_level": data["delay_risk_level"],
        "route_cost_score": float(data["route_cost_score"]),
        "created_at": data.get("created_at", utc_now()),
    }


def build_route_model_run_document(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_type": data["run_type"],
        "model_name": data["model_name"],
        "artifact_source": data["artifact_source"],
        "metrics_snapshot": data.get("metrics_snapshot", {}),
        "status": data.get("status", "completed"),
        "created_at": data.get("created_at", utc_now()),
        "created_by": data.get("created_by"),
    }


def safe_route_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    return serialize_mongo_document(document)


async def ensure_route_indexes() -> None:
    db = get_database()
    if db is None:
        return

    try:
        route_plans = db[ROUTE_PLAN_COLLECTION]
        await route_plans.create_index([("route_code", ASCENDING)], unique=True, name="unique_route_code")
        await route_plans.create_index([("status", ASCENDING)], name="route_plan_status")
        await route_plans.create_index([("vehicle_id", ASCENDING)], name="route_plan_vehicle")
        await route_plans.create_index([("driver_id", ASCENDING)], name="route_plan_driver")
        await route_plans.create_index([("created_at", DESCENDING)], name="route_plan_created_at")

        route_segments = db[ROUTE_SEGMENT_COLLECTION]
        await route_segments.create_index([("route_plan_id", ASCENDING)], name="route_segment_plan")
        await route_segments.create_index([("delay_risk_level", ASCENDING)], name="route_segment_delay_risk")
        await route_segments.create_index([("created_at", DESCENDING)], name="route_segment_created_at")

        await db[ROUTE_MODEL_RUN_COLLECTION].create_index([("created_at", DESCENDING)], name="route_model_run_created_at")
    except PyMongoError:
        return
