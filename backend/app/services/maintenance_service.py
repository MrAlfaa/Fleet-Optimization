import re
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.inspection_model import (
    INSPECTION_COLLECTION,
    WORK_ORDER_TERMINAL_STATUSES,
    validate_work_order_transition,
)
from app.models.maintenance_model import (
    MAINTENANCE_COLLECTION,
    MAINTENANCE_PRIORITIES,
    MAINTENANCE_SYSTEMS,
    build_maintenance_document,
    safe_maintenance_document,
)
from app.models.predictive_model import PREDICTION_COLLECTION
from app.models.maintenance_intelligence_model import PREDICTION_REVIEW_COLLECTION
from app.models.user_model import utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.models.vehicle_part_model import VEHICLE_PART_COLLECTION
from app.services.alert_service import create_maintenance_alert
from app.services.ml_model_loader_service import ModelUnavailableError
from app.services.vehicle_part_service import reset_part_after_maintenance
from app.utils.object_id import serialize_mongo_list, validate_object_id
from app.utils.pagination import build_pagination_response, calculate_skip, normalize_pagination


def get_maintenance_collection():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db[MAINTENANCE_COLLECTION]


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db


async def _prepare_record_data(data: dict[str, Any]) -> dict[str, Any]:
    prepared = data.copy()
    prepared.pop("review_id", None)
    try:
        prepared["vehicle_id"] = validate_object_id(prepared["vehicle_id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle ID") from exc

    vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": prepared["vehicle_id"]})
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    if prepared.get("part_id"):
        try:
            prepared["part_id"] = validate_object_id(prepared["part_id"])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid part ID") from exc
        part = await _db()[VEHICLE_PART_COLLECTION].find_one({"_id": prepared["part_id"], "vehicle_id": prepared["vehicle_id"]})
        if part is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle part not found")
    if prepared.get("prediction_review_id"):
        try:
            prepared["prediction_review_id"] = validate_object_id(prepared["prediction_review_id"])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid prediction review ID") from exc
        review = await _db()[PREDICTION_REVIEW_COLLECTION].find_one({"_id": prepared["prediction_review_id"]})
        if review is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engineering review not found")
        if review.get("vehicle_id") != prepared["vehicle_id"]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Engineering review belongs to another vehicle")
        if review.get("status") != "confirmed":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Engineering review must be confirmed before maintenance is linked")
        if review.get("linked_maintenance_record_id"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Engineering review is already linked to a maintenance record",
            )
    return prepared


async def create_maintenance_record(data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    prepared = await _prepare_record_data(data)
    try:
        created_by = validate_object_id(current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID") from exc

    document = build_maintenance_document(prepared, created_by)
    try:
        result = await get_maintenance_collection().insert_one(document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Engineering review is already linked to a maintenance record",
        ) from exc
    created = await get_maintenance_collection().find_one({"_id": result.inserted_id})
    if prepared.get("prediction_review_id"):
        link_result = await _db()[PREDICTION_REVIEW_COLLECTION].update_one(
            {
                "_id": prepared["prediction_review_id"],
                "vehicle_id": prepared["vehicle_id"],
                "status": "confirmed",
                "$or": [
                    {"linked_maintenance_record_id": {"$exists": False}},
                    {"linked_maintenance_record_id": None},
                ],
            },
            {"$set": {"linked_maintenance_record_id": result.inserted_id, "updated_at": utc_now()}},
        )
        if link_result.matched_count == 0:
            await get_maintenance_collection().delete_one({"_id": result.inserted_id})
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Engineering review is already linked to a maintenance record",
            )

    if created["priority"] in {"high", "critical"}:
        severity = "critical" if created["priority"] == "critical" else "high"
        await create_maintenance_alert(
            str(created["vehicle_id"]),
            str(created["part_id"]) if created.get("part_id") else None,
            severity,
            f"{created['priority'].title()} priority {created['maintenance_type']} maintenance scheduled for {created['part_name']}.",
            str(created["_id"]),
        )

    return safe_maintenance_document(created)


async def list_maintenance_records(
    vehicle_id: str | None = None,
    status_filter: str | None = None,
    priority: str | None = None,
    maintenance_type: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    query: dict[str, Any] = {}
    if vehicle_id:
        try:
            query["vehicle_id"] = validate_object_id(vehicle_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle ID") from exc
    if status_filter:
        query["status"] = status_filter
    if priority:
        query["priority"] = priority
    if maintenance_type:
        query["maintenance_type"] = maintenance_type
    if search:
        search_regex = re.compile(re.escape(search), re.IGNORECASE)
        query["$or"] = [{"part_name": search_regex}, {"issue_type": search_regex}, {"notes": search_regex}]

    collection = get_maintenance_collection()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("service_date", -1).skip(calculate_skip(page, limit)).limit(limit)
    return build_pagination_response(serialize_mongo_list(await cursor.to_list(length=limit)), total, page, limit)


async def get_maintenance_record_by_id(record_id: str) -> dict[str, Any] | None:
    try:
        object_id = validate_object_id(record_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid maintenance record ID") from exc
    return safe_maintenance_document(await get_maintenance_collection().find_one({"_id": object_id}))


async def update_maintenance_record(record_id: str, data: dict[str, Any]) -> dict[str, Any]:
    try:
        object_id = validate_object_id(record_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid maintenance record ID") from exc

    existing = await get_maintenance_collection().find_one({"_id": object_id})
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found")
    if existing.get("work_order_status") in WORK_ORDER_TERMINAL_STATUSES or existing.get("status") in {
        "completed", "cancelled"
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Terminal maintenance records are immutable")

    update_data = {key: value for key, value in data.items() if value is not None}
    protected = {
        "status", "work_order_status", "approved_by", "approved_at", "started_by", "started_at",
        "completed_by", "completed_at", "completion_evidence", "actual_cost", "cancelled_by",
        "cancelled_at", "cancellation_reason", "inspection_id", "assessment_id",
    }
    if protected.intersection(update_data):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Use the work-order lifecycle actions")
    if "part_id" in update_data and update_data["part_id"]:
        try:
            update_data["part_id"] = validate_object_id(update_data["part_id"])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid part ID") from exc
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")
    update_data["updated_at"] = utc_now()
    result = await get_maintenance_collection().update_one({"_id": object_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found")
    return safe_maintenance_document(await get_maintenance_collection().find_one({"_id": object_id}))


def _actor_id(current_user: dict[str, Any]):
    try:
        return validate_object_id(current_user["id"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID") from exc


async def create_inspection_work_order(
    inspection: dict[str, Any], data: dict[str, Any], review: dict[str, Any] | None,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    maintenance_system = str(data.get("maintenance_system") or "")
    priority = str(data.get("priority") or "")
    if maintenance_system not in MAINTENANCE_SYSTEMS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid maintenance system")
    if priority not in MAINTENANCE_PRIORITIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid maintenance priority")
    issue_type = str(data.get("issue_type") or "").strip()
    if not issue_type:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Issue type is required")
    try:
        estimated_cost = float(data["estimated_cost"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Estimated cost is required") from exc
    if estimated_cost < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Estimated cost cannot be negative")

    collection = get_maintenance_collection()
    active = await collection.find_one({
        "inspection_id": inspection["_id"],
        "work_order_status": {"$in": ["planned", "approved", "in_progress"]},
    })
    if active is not None:
        return safe_maintenance_document(active) or {}

    vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": inspection["vehicle_id"]})
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    now = utc_now()
    document = build_maintenance_document({
        "vehicle_id": inspection["vehicle_id"],
        "part_name": maintenance_system.replace("_", " ").title(),
        "maintenance_type": "corrective",
        "maintenance_system": maintenance_system,
        "event_kind": "corrective_repair",
        "issue_type": issue_type,
        "service_date": now,
        "mileage_at_service": float(vehicle.get("current_mileage") or vehicle.get("mileage") or 0),
        "status": "scheduled",
        "priority": priority,
        "notes": str(data.get("notes") or "").strip() or None,
        "inspection_id": inspection["_id"],
        "assessment_id": inspection["assessment_id"],
        "prediction_review_id": review.get("_id") if review else None,
        "work_order_status": "planned",
        "estimated_cost": estimated_cost,
    }, _actor_id(current_user))
    try:
        inserted = await collection.insert_one(document)
    except DuplicateKeyError as exc:
        active = await collection.find_one({
            "inspection_id": inspection["_id"],
            "work_order_status": {"$in": ["planned", "approved", "in_progress"]},
        })
        if active is not None:
            return safe_maintenance_document(active) or {}
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inspection already has an active work order") from exc
    document["_id"] = inserted.inserted_id
    return safe_maintenance_document(document) or {}


async def _work_order_transition(
    record_id: str,
    expected: str,
    target: str,
    changes: dict[str, Any],
) -> dict[str, Any]:
    validate_work_order_transition(expected, target, changes)
    object_id = validate_object_id(record_id)
    current = await get_maintenance_collection().find_one({"_id": object_id})
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found")
    if current.get("work_order_status") == target:
        return safe_maintenance_document(current) or {}
    legacy_status = "in_progress" if target == "in_progress" else "completed" if target == "completed" else "cancelled" if target == "cancelled" else "scheduled"
    row = await get_maintenance_collection().find_one_and_update(
        {"_id": object_id, "work_order_status": expected},
        {"$set": {**changes, "work_order_status": target, "status": legacy_status, "updated_at": utc_now()}},
        return_document=ReturnDocument.AFTER,
    )
    if row is None:
        existing = await get_maintenance_collection().find_one({"_id": object_id})
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found")
        if existing.get("work_order_status") == target:
            return safe_maintenance_document(existing) or {}
        if existing.get("work_order_status") in WORK_ORDER_TERMINAL_STATUSES:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Terminal maintenance records are immutable")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Work order cannot transition from {existing.get('work_order_status')} to {target}",
        )
    return safe_maintenance_document(row) or {}


async def approve_maintenance_record(record_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return await _work_order_transition(record_id, "planned", "approved", {
        "approved_by": _actor_id(current_user), "approved_at": now,
    })


async def start_maintenance_record(record_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return await _work_order_transition(record_id, "approved", "in_progress", {
        "started_by": _actor_id(current_user), "started_at": now,
    })


async def _recalculate_after_completion(
    vehicle_id: str, current_user: dict[str, Any]
) -> dict[str, Any] | None:
    from app.services.predictive_maintenance_service import recalculate_vehicle_maintenance

    return await recalculate_vehicle_maintenance(
        vehicle_id, {"trigger": "maintenance_completed"}, current_user
    )


async def _release_vehicle_if_ready(
    record: dict[str, Any], *, reassessment_succeeded: bool
) -> bool:
    if not reassessment_succeeded:
        return False
    vehicle_id = record["vehicle_id"]
    vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": vehicle_id})
    if vehicle is None or vehicle.get("status") in {"inactive", "retired"} or vehicle.get("health_status") == "critical":
        return False
    review = await _db()[PREDICTION_REVIEW_COLLECTION].find_one({
        "vehicle_id": vehicle_id, "status": {"$in": ["pending", "confirmed"]},
    })
    if review is not None:
        return False
    assessment = await _db()[PREDICTION_COLLECTION].find_one(
        {"vehicle_id": vehicle_id}, sort=[("created_at", -1)]
    )
    if assessment is None or assessment.get("dispatch_hold") is True:
        return False
    other_inspection = await _db()[INSPECTION_COLLECTION].find_one({
        "vehicle_id": vehicle_id,
        "is_active": True,
        "_id": {"$ne": record.get("inspection_id")},
    })
    if other_inspection is not None:
        return False
    other_work = await get_maintenance_collection().find_one({
        "vehicle_id": vehicle_id,
        "_id": {"$ne": record["_id"]},
        "$or": [
            {"work_order_status": {"$in": ["planned", "approved", "in_progress"]}},
            {
                "work_order_status": {"$exists": False},
                "status": {"$in": ["scheduled", "in_progress"]},
            },
        ],
    })
    if other_work is not None:
        return False
    await _db()[VEHICLE_COLLECTION].update_one(
        {"_id": vehicle_id, "status": "under_maintenance"},
        {"$set": {"status": "active", "updated_at": utc_now()}},
    )
    return True


async def complete_maintenance_record(record_id: str, completion_data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        object_id = validate_object_id(record_id)
        resolver_id = validate_object_id(current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID") from exc

    record = await get_maintenance_collection().find_one({"_id": object_id})
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found")

    try:
        actual_cost = float(completion_data["actual_cost"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Actual cost is required") from exc
    evidence = str(completion_data.get("completion_evidence") or "").strip()
    if actual_cost < 0 or not evidence:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Valid actual cost and completion evidence are required",
        )
    if record.get("work_order_status") == "completed" and record.get("status") == "completed":
        if float(record.get("actual_cost", -1)) == actual_cost and record.get("completion_evidence") == evidence:
            return safe_maintenance_document(record) or {}
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Terminal maintenance records are immutable")

    now = utc_now()
    update_data = {key: value for key, value in completion_data.items() if value is not None}
    update_data.update({
        "actual_cost": actual_cost,
        "cost": actual_cost,
        "completion_evidence": evidence,
        "completed_by": resolver_id,
        "completed_at": now,
    })
    validate_work_order_transition("in_progress", "completed", update_data)
    completed = await get_maintenance_collection().find_one_and_update(
        {
            "_id": object_id,
            "status": "in_progress",
            "work_order_status": {"$in": ["in_progress", None]},
        },
        {"$set": {
            **update_data,
            "status": "completed",
            "work_order_status": "completed",
            "updated_at": now,
        }},
        return_document=ReturnDocument.AFTER,
    )
    if completed is None:
        if record.get("work_order_status") in WORK_ORDER_TERMINAL_STATUSES or record.get("status") in {
            "completed", "cancelled"
        }:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Terminal maintenance records are immutable")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only in-progress work orders can be completed")
    record = completed
    await _db()[VEHICLE_COLLECTION].update_one(
        {"_id": record["vehicle_id"]},
        {"$set": {"last_service_date": record["service_date"], "updated_at": now}},
    )

    if record.get("part_id"):
        await _db()[VEHICLE_PART_COLLECTION].update_one(
            {"_id": record["part_id"]},
            {"$set": {"last_serviced_date": record["service_date"], "updated_at": now}},
        )
        await reset_part_after_maintenance(str(record["part_id"]))

    alert_update = {
        "$set": {
            "status": "resolved",
            "resolved_at": now,
            "resolved_by": resolver_id,
        }
    }
    result = await _db()[ALERT_COLLECTION].update_many(
        {"linked_maintenance_record_id": object_id, "status": "active"},
        alert_update,
    )
    if result.matched_count == 0:
        await create_maintenance_alert(
            str(record["vehicle_id"]),
            str(record["part_id"]) if record.get("part_id") else None,
            "info",
            f"Maintenance completed for {record['part_name']}.",
            str(record["_id"]),
        )
        await _db()[ALERT_COLLECTION].update_one(
            {"linked_maintenance_record_id": object_id, "message": f"Maintenance completed for {record['part_name']}."},
            alert_update,
        )

    from app.services.predictive_maintenance_service import clear_reviews_for_completed_maintenance
    await clear_reviews_for_completed_maintenance(record, current_user)
    reassessment_succeeded = False
    try:
        await _recalculate_after_completion(str(record["vehicle_id"]), current_user)
        reassessment_succeeded = True
    except (ModelUnavailableError, HTTPException, ValueError):
        # Completion is retained, but release requires a successful fresh readiness result.
        pass

    if record.get("inspection_id"):
        await _db()[INSPECTION_COLLECTION].find_one_and_update(
            {
                "_id": record["inspection_id"],
                "work_order_id": object_id,
                "status": "maintenance_required",
                "is_active": True,
            },
            {"$set": {
                "is_active": False,
                "maintenance_completed_at": now,
                "maintenance_completed_by": resolver_id,
                "updated_at": now,
            }},
            return_document=ReturnDocument.AFTER,
        )
    await _release_vehicle_if_ready(record, reassessment_succeeded=reassessment_succeeded)

    return safe_maintenance_document(await get_maintenance_collection().find_one({"_id": object_id}))


async def cancel_maintenance_record(
    record_id: str, data: dict[str, Any], current_user: dict[str, Any]
) -> dict[str, Any]:
    reason = str(data.get("reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Cancellation reason is required")
    now = utc_now()
    changes = {
        "cancelled_by": _actor_id(current_user),
        "cancelled_at": now,
        "cancellation_reason": reason,
    }
    object_id = validate_object_id(record_id)
    row = await get_maintenance_collection().find_one_and_update(
        {"_id": object_id, "work_order_status": {"$in": ["planned", "approved", "in_progress"]}},
        {"$set": {
            **changes,
            "work_order_status": "cancelled",
            "status": "cancelled",
            "updated_at": now,
        }},
        return_document=ReturnDocument.AFTER,
    )
    if row is None:
        existing = await get_maintenance_collection().find_one({"_id": object_id})
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found")
        if (
            existing.get("work_order_status") == "cancelled"
            and existing.get("cancellation_reason") == reason
        ):
            return safe_maintenance_document(existing) or {}
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Terminal maintenance records are immutable")
    return safe_maintenance_document(row) or {}


async def get_maintenance_summary() -> dict[str, int]:
    collection = get_maintenance_collection()
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return {
        "scheduled": await collection.count_documents({"status": "scheduled"}),
        "in_progress": await collection.count_documents({"status": "in_progress"}),
        "completed": await collection.count_documents({"status": "completed"}),
        "cancelled": await collection.count_documents({"status": "cancelled"}),
        "high_priority": await collection.count_documents({"priority": "high"}),
        "critical_priority": await collection.count_documents({"priority": "critical"}),
        "completed_this_month": await collection.count_documents({"status": "completed", "service_date": {"$gte": month_start}}),
    }
