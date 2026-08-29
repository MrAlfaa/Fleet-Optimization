from __future__ import annotations

from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.maintenance_intelligence_model import (
    FEATURE_SNAPSHOT_COLLECTION, PREDICTION_REVIEW_COLLECTION,
    build_feature_snapshot_document, build_prediction_review_document,
)
from app.models.predictive_model import PREDICTION_COLLECTION, build_prediction_document, safe_prediction_document
from app.models.user_model import utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.services.alert_service import create_alert
from app.services.maintenance_feature_service import build_vehicle_features
from app.services.maintenance_eligibility_service import get_assessment_eligibility
from app.services.maintenance_inference_service import infer_maintenance
from app.services.predictive_artifact_registry import predictive_artifact_registry
from app.utils.object_id import serialize_mongo_document, validate_object_id
from app.utils.pagination import build_pagination_response, calculate_skip, normalize_pagination


PREDICTIVE_ALLOWED_ROLES = ["admin", "fleet_manager", "maintenance_manager"]
REVIEW_RESOLVER_ROLES = ["admin", "maintenance_manager"]
ACTIVE_REVIEW_STATUSES = {"pending", "confirmed"}


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB is not configured or connected")
    return db


def _oid(value: str, name: str = "id") -> ObjectId:
    try:
        return validate_object_id(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {name}") from exc


def _user_oid(current_user: dict[str, Any]) -> ObjectId | None:
    value = current_user.get("id")
    return _oid(str(value), "user ID") if value else None


def _apply_prediction_review_state(prediction: dict[str, Any], review: dict[str, Any] | None) -> dict[str, Any]:
    result = dict(prediction)
    review_status = str((review or {}).get("status") or prediction.get("review_status") or "not_required")
    result["review_status"] = review_status
    result["dispatch_hold"] = review_status in ACTIVE_REVIEW_STATUSES or (
        review is None and bool(prediction.get("dispatch_hold"))
    )
    result["review_id"] = str(review.get("_id") or review.get("id")) if review else None
    result["policy_decision"] = "hold_for_engineering_review" if result["dispatch_hold"] else "operation_allowed"
    return result


def _public_prediction(prediction: dict[str, Any], vehicle: dict[str, Any] | None = None) -> dict[str, Any]:
    result = safe_prediction_document(prediction) or {}
    result.pop("input_features", None)
    result["vehicle_registration"] = (vehicle or {}).get("registration_number") or (vehicle or {}).get("vehicle_code")
    result["vehicle_code"] = (vehicle or {}).get("vehicle_code")
    return result


def _public_review(
    review: dict[str, Any], vehicle: dict[str, Any] | None, prediction: dict[str, Any] | None
) -> dict[str, Any]:
    result = serialize_mongo_document(review) or {}
    result["vehicle_registration"] = (vehicle or {}).get("registration_number") or (vehicle or {}).get("vehicle_code")
    result["vehicle_code"] = (vehicle or {}).get("vehicle_code")
    result["risk_level"] = (prediction or {}).get("risk_level") or "unknown"
    result["system_risks"] = list((prediction or {}).get("system_risks") or [])[:3]
    result["maintenance_system"] = (prediction or {}).get("maintenance_type_name")
    return result


async def _vehicle_map(vehicle_ids: set[ObjectId]) -> dict[ObjectId, dict[str, Any]]:
    if not vehicle_ids:
        return {}
    rows = await _db()[VEHICLE_COLLECTION].find({"_id": {"$in": list(vehicle_ids)}}).to_list(length=len(vehicle_ids))
    return {row["_id"]: row for row in rows}


async def _find_existing_prediction(vehicle_id: ObjectId, feature_hash: str, model_version: str) -> dict[str, Any] | None:
    return await _db()[PREDICTION_COLLECTION].find_one(
        {"vehicle_id": vehicle_id, "feature_hash": feature_hash, "model_version": model_version},
        sort=[("created_at", -1)],
    )


async def _find_review_for_hash(vehicle_id: ObjectId, feature_hash: str) -> dict[str, Any] | None:
    return await _db()[PREDICTION_REVIEW_COLLECTION].find_one(
        {"vehicle_id": vehicle_id, "feature_hash": feature_hash}, sort=[("created_at", -1)]
    )


async def _get_vehicle(vehicle_id: ObjectId) -> dict[str, Any] | None:
    return await _db()[VEHICLE_COLLECTION].find_one({"_id": vehicle_id})


async def _cache_vehicle_assessment_risk(vehicle_id: ObjectId, risk_level: str) -> None:
    now = utc_now()
    await _db()[VEHICLE_COLLECTION].update_one(
        {"_id": vehicle_id},
        {"$set": {
            "latest_assessment_risk": risk_level,
            "latest_assessment_at": now,
            "updated_at": now,
        }},
    )


async def _persist_snapshot(vehicle_id, feature_result, trigger, metadata, current_user, artifacts):
    document = build_feature_snapshot_document({
        "vehicle_id": vehicle_id, "trigger": trigger, "trigger_metadata": metadata,
        "features": feature_result.features, "feature_hash": feature_result.feature_hash,
        "source_ids": feature_result.source_ids, "defaulted_fields": feature_result.defaulted_fields,
        "quality_grade": feature_result.quality_grade, "model_version": artifacts.model_version,
        "feature_schema_version": artifacts.feature_schema_version, "created_by": _user_oid(current_user),
    })
    return (await _db()[FEATURE_SNAPSHOT_COLLECTION].insert_one(document)).inserted_id


async def _persist_prediction(data: dict[str, Any]) -> dict[str, Any]:
    document = build_prediction_document(data)
    document["_id"] = (await _db()[PREDICTION_COLLECTION].insert_one(document)).inserted_id
    return safe_prediction_document(document) or {}


async def _create_review_alert(vehicle: dict[str, Any], review_id: ObjectId, prediction: dict[str, Any]) -> None:
    title = f"Engineering review required - {vehicle.get('registration_number') or vehicle.get('vehicle_code')}"
    if await _db()[ALERT_COLLECTION].find_one({"title": title, "status": "active"}):
        return
    await create_alert({
        "alert_type": "maintenance", "severity": "critical" if prediction.get("risk_level") == "critical" else "high",
        "title": title, "message": prediction.get("recommended_action") or "Review the latest maintenance risk result.",
        "linked_vehicle_id": str(vehicle["_id"]), "linked_prediction_review_id": str(review_id),
        "created_by_system": True,
    })


async def _create_review(vehicle, prediction, feature_hash, current_user):
    prediction_id = _oid(str(prediction.get("id") or prediction.get("_id")), "prediction ID")
    document = build_prediction_review_document({
        "vehicle_id": vehicle["_id"], "prediction_id": prediction_id, "feature_hash": feature_hash,
        "created_by": _user_oid(current_user),
    })
    document["_id"] = (await _db()[PREDICTION_REVIEW_COLLECTION].insert_one(document)).inserted_id
    await _create_review_alert(vehicle, document["_id"], prediction)
    return document


async def recalculate_vehicle_maintenance(vehicle_id: str, trigger_metadata: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    vehicle_oid = _oid(vehicle_id, "vehicle ID")
    vehicle = await _get_vehicle(vehicle_oid)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    eligibility = await get_assessment_eligibility(vehicle_id)
    if not eligibility["eligible"]:
        reason = "; ".join(eligibility["blocking_reasons"]) or "Vehicle is not ready for assessment"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Assessment is not ready: {reason}")
    artifacts = predictive_artifact_registry.get()
    feature_result = await build_vehicle_features(vehicle_id)
    existing = await _find_existing_prediction(vehicle_oid, feature_result.feature_hash, artifacts.model_version)
    existing_review = await _find_review_for_hash(vehicle_oid, feature_result.feature_hash)
    if existing:
        public = _public_prediction(existing, vehicle)
        review_required = (
            bool(trigger_metadata.get("request_review"))
            or existing.get("risk_level") == "critical"
            or bool(existing.get("dispatch_hold"))
        )
        if review_required and existing_review is None:
            existing_review = await _create_review(vehicle, public, feature_result.feature_hash, current_user)
            await _db()[PREDICTION_COLLECTION].update_one(
                {"_id": existing["_id"]},
                {"$set": {"review_status": "pending", "dispatch_hold": True,
                          "policy_decision": "hold_for_engineering_review"}},
            )
        await _cache_vehicle_assessment_risk(vehicle_oid, str(existing.get("risk_level") or "low"))
        return _apply_prediction_review_state(public, serialize_mongo_document(existing_review))

    trigger = str(trigger_metadata.get("trigger") or "manual_recalculation")
    snapshot_id = await _persist_snapshot(vehicle_oid, feature_result, trigger, trigger_metadata, current_user, artifacts)
    inference = infer_maintenance(feature_result.features, artifacts)
    should_review = inference["risk_level"] == "critical" or bool(trigger_metadata.get("request_review"))
    prediction = await _persist_prediction({
        **inference, "vehicle_id": vehicle_oid, "input_source": trigger, "input_features": {},
        "failure_prediction": int(float(inference["normalized_risk"]) >= 1.0),
        "feature_snapshot_id": snapshot_id, "feature_hash": feature_result.feature_hash,
        "feature_schema_version": artifacts.feature_schema_version, "data_quality": feature_result.quality_grade,
        "defaulted_fields": feature_result.defaulted_fields,
        "review_status": "pending" if should_review else "not_required", "dispatch_hold": should_review,
        "policy_decision": "hold_for_engineering_review" if should_review else "operation_allowed",
        "model_version": artifacts.model_version,
        "model_metrics_snapshot": {"quality_gate": artifacts.metrics.get("quality_gate", {})},
        "created_by": _user_oid(current_user),
    })
    review = existing_review
    if should_review and review is None:
        review = await _create_review(vehicle, prediction, feature_result.feature_hash, current_user)
    prediction = _apply_prediction_review_state(_public_prediction(prediction, vehicle), serialize_mongo_document(review))
    prediction_id = prediction.get("id") or prediction.get("_id")
    if prediction_id:
        await _db()[PREDICTION_COLLECTION].update_one(
            {"_id": _oid(str(prediction_id), "prediction ID")},
            {"$set": {key: prediction[key] for key in ("review_status", "dispatch_hold", "policy_decision")}},
        )
    await _cache_vehicle_assessment_risk(vehicle_oid, str(prediction.get("risk_level") or "low"))
    return prediction


async def predict_vehicle_maintenance(request: Any, current_user: dict[str, Any]) -> dict[str, Any]:
    payload = request.model_dump(exclude={"vehicle_id"}) if hasattr(request, "model_dump") else dict(request)
    vehicle_id = request.vehicle_id if hasattr(request, "vehicle_id") else payload.pop("vehicle_id")
    return await recalculate_vehicle_maintenance(str(vehicle_id), payload, current_user)


async def predict_batch_maintenance(request: Any, current_user: dict[str, Any]) -> dict[str, Any]:
    return {"items": [await predict_vehicle_maintenance(item, current_user) for item in request.requests]}


async def get_model_status(load_model: bool = True) -> dict[str, Any]:
    return predictive_artifact_registry.status()


async def get_current_vehicle_prediction(vehicle_id: str) -> dict[str, Any] | None:
    oid = _oid(vehicle_id, "vehicle ID")
    prediction = await _db()[PREDICTION_COLLECTION].find_one({"vehicle_id": oid}, sort=[("created_at", -1)])
    if prediction is None:
        return None
    review = await _find_review_for_hash(oid, str(prediction.get("feature_hash") or ""))
    vehicle = await _get_vehicle(oid)
    return _apply_prediction_review_state(_public_prediction(prediction, vehicle), serialize_mongo_document(review))


async def get_vehicle_prediction_history(vehicle_id: str, limit: int = 20) -> list[dict[str, Any]]:
    oid = _oid(vehicle_id, "vehicle ID")
    rows = await _db()[PREDICTION_COLLECTION].find({"vehicle_id": oid}).sort("created_at", -1).limit(limit).to_list(length=limit)
    vehicle = await _get_vehicle(oid)
    return [_public_prediction(row, vehicle) for row in rows]


async def get_prediction_by_id(prediction_id: str) -> dict[str, Any] | None:
    prediction = await _db()[PREDICTION_COLLECTION].find_one({"_id": _oid(prediction_id, "prediction ID")})
    if prediction is None:
        return None
    return _public_prediction(prediction, await _get_vehicle(prediction["vehicle_id"]))


async def list_predictions(vehicle_id=None, risk_level=None, page=1, limit=20):
    page, limit = normalize_pagination(page, limit)
    query: dict[str, Any] = {}
    if vehicle_id:
        query["vehicle_id"] = _oid(vehicle_id, "vehicle ID")
    if risk_level:
        query["risk_level"] = risk_level
    collection = _db()[PREDICTION_COLLECTION]
    total = await collection.count_documents(query)
    rows = await collection.find(query).sort("created_at", -1).skip(calculate_skip(page, limit)).limit(limit).to_list(length=limit)
    vehicles = await _vehicle_map({row["vehicle_id"] for row in rows if isinstance(row.get("vehicle_id"), ObjectId)})
    return build_pagination_response([_public_prediction(row, vehicles.get(row.get("vehicle_id"))) for row in rows], total, page, limit)


async def get_fleet_risk_summary() -> dict[str, Any]:
    latest: dict[ObjectId, dict[str, Any]] = {}
    async for row in _db()[PREDICTION_COLLECTION].find({}).sort("created_at", -1):
        latest.setdefault(row["vehicle_id"], row)
    counts = {level: 0 for level in ("low", "medium", "high", "critical")}
    for row in latest.values():
        counts[str(row.get("risk_level") or "low")] += 1
    return {**counts, "total": len(latest)}


async def get_predictive_dashboard_metrics() -> dict[str, Any]:
    summary = await get_fleet_risk_summary()
    pending_reviews = await _db()[PREDICTION_REVIEW_COLLECTION].count_documents(
        {"status": {"$in": ["pending", "confirmed"]}}
    )
    return {
        "total_predictions": summary["total"],
        "low_risk": summary["low"],
        "medium_risk": summary["medium"],
        "high_risk": summary["high"],
        "critical_risk": summary["critical"],
        "engineering_review_holds": pending_reviews,
        "model_status": predictive_artifact_registry.status(),
    }


async def list_prediction_reviews(status_filter=None, page=1, limit=50):
    page, limit = normalize_pagination(page, limit)
    query = {"status": status_filter} if status_filter else {}
    collection = _db()[PREDICTION_REVIEW_COLLECTION]
    total = await collection.count_documents(query)
    rows = await collection.find(query).sort("created_at", -1).skip(calculate_skip(page, limit)).limit(limit).to_list(length=limit)
    vehicles = await _vehicle_map({row["vehicle_id"] for row in rows if isinstance(row.get("vehicle_id"), ObjectId)})
    prediction_ids = [row["prediction_id"] for row in rows if isinstance(row.get("prediction_id"), ObjectId)]
    prediction_rows = await _db()[PREDICTION_COLLECTION].find({"_id": {"$in": prediction_ids}}).to_list(length=len(prediction_ids) or 1)
    predictions = {row["_id"]: row for row in prediction_rows}
    items = [_public_review(row, vehicles.get(row.get("vehicle_id")), predictions.get(row.get("prediction_id"))) for row in rows]
    return build_pagination_response(items, total, page, limit)


async def resolve_prediction_review(
    review_id: str,
    data: dict[str, Any],
    current_user: dict[str, Any],
    *,
    allow_confirmed_clear: bool = False,
) -> dict[str, Any]:
    oid = _oid(review_id, "review ID")
    review = await _db()[PREDICTION_REVIEW_COLLECTION].find_one({"_id": oid})
    if review is None:
        raise HTTPException(status_code=404, detail="Engineering review not found")
    resolution, now = str(data["resolution"]), utc_now()
    if review.get("status") == "confirmed" and resolution == "cleared" and not allow_confirmed_clear:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A confirmed issue remains blocked until its linked maintenance work is completed",
        )
    update = {
        "status": resolution, "resolution": resolution, "notes": data["notes"], "resolved_at": now,
        "resolved_by": _user_oid(current_user), "updated_at": now,
    }
    await _db()[PREDICTION_REVIEW_COLLECTION].update_one({"_id": oid}, {"$set": update})
    hold = resolution == "confirmed"
    await _db()[PREDICTION_COLLECTION].update_many(
        {"vehicle_id": review["vehicle_id"], "feature_hash": review["feature_hash"]},
        {"$set": {"review_status": resolution, "dispatch_hold": hold,
                  "policy_decision": "hold_for_maintenance" if hold else "operation_allowed"}},
    )
    if not hold:
        await _db()[ALERT_COLLECTION].update_many(
            {"linked_prediction_review_id": oid, "status": "active"},
            {"$set": {"status": "resolved", "resolved_at": now, "resolved_by": _user_oid(current_user)}},
        )
    return serialize_mongo_document({**review, **update}) or {}


async def clear_reviews_for_completed_maintenance(record: dict[str, Any], current_user: dict[str, Any]) -> None:
    reviews = await _db()[PREDICTION_REVIEW_COLLECTION].find({
        "vehicle_id": record["vehicle_id"], "status": "confirmed",
        "linked_maintenance_record_id": record["_id"],
    }).to_list(length=100)
    for review in reviews:
        await resolve_prediction_review(str(review["_id"]), {
            "resolution": "cleared", "notes": "Linked maintenance work completed."
        }, current_user, allow_confirmed_clear=True)
