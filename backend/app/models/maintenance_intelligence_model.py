from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document


FEATURE_SNAPSHOT_COLLECTION = "maintenance_feature_snapshots"
PREDICTION_REVIEW_COLLECTION = "maintenance_prediction_reviews"
PREDICTION_REVIEW_STATUSES = {"pending", "cleared", "confirmed"}
PREDICTION_REVIEW_RESOLUTIONS = {"cleared", "confirmed"}


def build_feature_snapshot_document(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "vehicle_id": data["vehicle_id"],
        "trigger": data["trigger"],
        "trigger_metadata": data.get("trigger_metadata", {}),
        "features": dict(data["features"]),
        "feature_hash": data["feature_hash"],
        "source_ids": dict(data.get("source_ids") or {}),
        "defaulted_fields": list(data.get("defaulted_fields") or []),
        "quality_grade": data["quality_grade"],
        "model_version": data["model_version"],
        "feature_schema_version": data["feature_schema_version"],
        "created_at": data.get("created_at") or utc_now(),
        "created_by": data.get("created_by"),
    }


def build_prediction_review_document(data: dict[str, Any]) -> dict[str, Any]:
    now = data.get("created_at") or utc_now()
    return {
        "vehicle_id": data["vehicle_id"],
        "prediction_id": data["prediction_id"],
        "feature_hash": data["feature_hash"],
        "status": data.get("status", "pending"),
        "resolution": data.get("resolution"),
        "notes": data.get("notes"),
        "created_by": data.get("created_by"),
        "created_at": now,
        "updated_at": data.get("updated_at") or now,
        "resolved_at": data.get("resolved_at"),
        "resolved_by": data.get("resolved_by"),
    }


def safe_maintenance_intelligence_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    return serialize_mongo_document(document)


async def ensure_maintenance_intelligence_indexes() -> None:
    db = get_database()
    if db is None:
        return
    try:
        snapshots = db[FEATURE_SNAPSHOT_COLLECTION]
        await snapshots.create_index([("vehicle_id", ASCENDING), ("created_at", DESCENDING)], name="feature_snapshot_vehicle_time")
        await snapshots.create_index([("vehicle_id", ASCENDING), ("feature_hash", ASCENDING)], name="feature_snapshot_vehicle_hash")
        reviews = db[PREDICTION_REVIEW_COLLECTION]
        await reviews.create_index([("vehicle_id", ASCENDING), ("status", ASCENDING)], name="prediction_review_vehicle_status")
        await reviews.create_index([("prediction_id", ASCENDING)], unique=True, name="unique_prediction_review")
        await reviews.create_index(
            [("vehicle_id", ASCENDING), ("feature_hash", ASCENDING)],
            unique=True,
            name="unique_prediction_review_feature",
        )
        await reviews.create_index([("created_at", DESCENDING)], name="prediction_review_created_at")
    except PyMongoError:
        return
