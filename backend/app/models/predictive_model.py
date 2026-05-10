from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document


PREDICTION_COLLECTION = "maintenance_predictions"

PREDICTION_RISK_LEVELS = {"low", "medium", "high", "critical"}
PREDICTION_INPUT_SOURCES = {"manual", "simulated", "imported", "api"}


def build_prediction_document(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "vehicle_id": data["vehicle_id"],
        "part_id": data.get("part_id"),
        "part_name": data.get("part_name"),
        "input_source": data["input_source"],
        "input_features": data["input_features"],
        "failure_prediction": int(data["failure_prediction"]),
        "failure_probability": float(data["failure_probability"]),
        "risk_level": data["risk_level"],
        "maintenance_type_id": data.get("maintenance_type_id"),
        "maintenance_type_name": data.get("maintenance_type_name"),
        "predicted_rul": data.get("predicted_rul"),
        "rul_unit": data.get("rul_unit"),
        "next_maintenance_date": data.get("next_maintenance_date"),
        "recommended_action": data["recommended_action"],
        "model_version": data.get("model_version"),
        "model_metrics_snapshot": data.get("model_metrics_snapshot"),
        "created_at": data.get("created_at", utc_now()),
        "created_by": data.get("created_by"),
    }


def safe_prediction_document(prediction: dict[str, Any] | None) -> dict[str, Any] | None:
    return serialize_mongo_document(prediction)


async def ensure_prediction_indexes() -> None:
    db = get_database()
    if db is None:
        return

    try:
        collection = db[PREDICTION_COLLECTION]
        await collection.create_index([("vehicle_id", ASCENDING)], name="prediction_vehicle_id")
        await collection.create_index([("part_id", ASCENDING)], name="prediction_part_id")
        await collection.create_index([("risk_level", ASCENDING)], name="prediction_risk_level")
        await collection.create_index([("created_at", DESCENDING)], name="prediction_created_at")
    except PyMongoError:
        return
