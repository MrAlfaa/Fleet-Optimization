from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.database import get_database
from app.models.inspection_model import (
    INSPECTION_COLLECTION,
    build_inspection_document,
    safe_inspection_document,
    validate_inspection_transition,
)
from app.models.predictive_model import PREDICTION_COLLECTION
from app.models.maintenance_intelligence_model import PREDICTION_REVIEW_COLLECTION
from app.models.maintenance_model import MAINTENANCE_COLLECTION
from app.models.user_model import USER_COLLECTION, utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.schemas.inspection_schema import InspectionAssigneeResponse
from app.utils.object_id import validate_object_id
from app.utils.pagination import build_pagination_response, calculate_skip, normalize_pagination


INSPECTION_VIEW_ROLES = ["admin", "fleet_manager", "maintenance_manager"]
INSPECTION_MANAGE_ROLES = ["admin", "maintenance_manager"]
INSPECTION_ASSIGNEE_ROLES = ["admin", "maintenance_manager"]
CANCELLABLE_STATUSES = ["pending", "assigned", "in_progress"]


def _db():
    database = get_database()
    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB is not configured or connected",
        )
    return database


def _oid(value: str, label: str) -> ObjectId:
    try:
        return validate_object_id(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {label}") from exc


def _actor_id(current_user: dict[str, Any]) -> ObjectId:
    value = current_user.get("id") or current_user.get("_id")
    if value is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid current user")
    return _oid(str(value), "user ID")


def _elapsed_seconds(document: dict[str, Any]) -> int | None:
    started_at = document.get("started_at")
    ended_at = document.get("completed_at") or document.get("cancelled_at")
    if not isinstance(started_at, datetime) or not isinstance(ended_at, datetime):
        return None
    return max(0, int((ended_at - started_at).total_seconds()))


def _public(document: dict[str, Any] | None) -> dict[str, Any] | None:
    serialized = safe_inspection_document(document)
    if serialized is not None:
        if (
            serialized.get("status") == "maintenance_required"
            and serialized.get("is_active") is False
            and serialized.get("maintenance_completed_at")
        ):
            serialized["status"] = "maintenance_completed"
        serialized.setdefault("draft_checklist", [])
        serialized.setdefault("draft_summary", None)
        serialized.setdefault("draft_saved_by", None)
        serialized.setdefault("draft_saved_at", None)
        serialized["elapsed_seconds"] = _elapsed_seconds(document or {})
    return serialized


async def list_inspections(
    status_filter: str | None = None,
    vehicle_id: str | None = None,
    assigned_to: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    query: dict[str, Any] = {}
    if status_filter:
        query["status"] = status_filter
    if vehicle_id:
        query["vehicle_id"] = _oid(vehicle_id, "vehicle ID")
    if assigned_to:
        query["assigned_to"] = _oid(assigned_to, "assignee ID")
    collection = _db()[INSPECTION_COLLECTION]
    total = await collection.count_documents(query)
    rows = await (
        collection.find(query)
        .sort([("is_active", -1), ("priority", -1), ("created_at", -1)])
        .skip(calculate_skip(page, limit))
        .limit(limit)
        .to_list(length=limit)
    )
    return build_pagination_response([_public(row) for row in rows], total, page, limit)


async def list_inspection_assignees() -> list[dict[str, str]]:
    rows = await _db()[USER_COLLECTION].find(
        {
            "role": {"$in": INSPECTION_ASSIGNEE_ROLES},
            "is_active": True,
        },
        {
            "full_name": 1,
            "role": 1,
        },
    ).to_list(length=None)
    assignees = [
        InspectionAssigneeResponse(
            id=str(row["_id"]),
            full_name=row["full_name"],
            role=row["role"],
        )
        for row in rows
    ]
    assignees.sort(key=lambda item: (item.full_name.casefold(), item.id))
    return [item.model_dump() for item in assignees]


async def get_inspection(inspection_id: str) -> dict[str, Any]:
    row = await _db()[INSPECTION_COLLECTION].find_one({"_id": _oid(inspection_id, "inspection ID")})
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    return _public(row) or {}


async def create_inspection(data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    vehicle_id = _oid(data["vehicle_id"], "vehicle ID")
    inspection_type = str(data.get("inspection_type") or "risk_assessment")
    if inspection_type == "commissioning":
        vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": vehicle_id})
        if vehicle is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
        if vehicle.get("status") == "retired":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Retired vehicles cannot be inspected")
        assessment_id = None
        feature_hash = f"commissioning:{vehicle_id}"
    else:
        assessment_id = _oid(data["assessment_id"], "assessment ID")
        assessment = await _db()[PREDICTION_COLLECTION].find_one({"_id": assessment_id})
        if assessment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
        if assessment.get("vehicle_id") != vehicle_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment must belong to the same vehicle",
            )
        feature_hash = str(data["feature_hash"])
        if str(assessment.get("feature_hash") or "") != feature_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment feature hash does not match",
            )

    collection = _db()[INSPECTION_COLLECTION]
    active = await collection.find_one({"vehicle_id": vehicle_id, "is_active": True})
    if active is not None:
        if active.get("assessment_id") == assessment_id and active.get("feature_hash") == feature_hash:
            return _public(active) or {}
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle already has an active inspection",
        )

    document = build_inspection_document(
        {
            **data,
            "vehicle_id": vehicle_id,
            "assessment_id": assessment_id,
            "feature_hash": feature_hash,
            "inspection_type": inspection_type,
        },
        _actor_id(current_user),
        now=utc_now(),
    )
    try:
        result = await collection.insert_one(document)
    except DuplicateKeyError as exc:
        active = await collection.find_one({"vehicle_id": vehicle_id, "is_active": True})
        if active and active.get("assessment_id") == assessment_id and active.get("feature_hash") == feature_hash:
            return _public(active) or {}
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle already has an active inspection",
        ) from exc
    document["_id"] = result.inserted_id
    if inspection_type == "commissioning":
        await _db()[VEHICLE_COLLECTION].update_one(
            {"_id": vehicle_id, "status": {"$ne": "retired"}},
            {"$set": {"commissioning_status": "pending", "updated_at": utc_now()}},
        )
    return _public(document) or {}


async def _transition(
    inspection_id: str,
    expected_status: str | dict[str, Any],
    target_status: str,
    changes: dict[str, Any],
    *,
    extra_filter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {
        "_id": _oid(inspection_id, "inspection ID"),
        "status": expected_status,
        "is_active": True,
        **(extra_filter or {}),
    }
    update = {**changes, "status": target_status, "updated_at": utc_now()}
    row = await _db()[INSPECTION_COLLECTION].find_one_and_update(
        query,
        {"$set": update},
        return_document=ReturnDocument.AFTER,
    )
    if row is None:
        existing = await _db()[INSPECTION_COLLECTION].find_one({"_id": query["_id"]})
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inspection cannot transition from {existing.get('status')} to {target_status}",
        )
    return _public(row) or {}


async def assign_inspection(
    inspection_id: str, data: dict[str, Any], current_user: dict[str, Any]
) -> dict[str, Any]:
    assignee_id = _oid(data["assigned_to"], "assignee ID")
    assignee = await _db()[USER_COLLECTION].find_one({
        "_id": assignee_id,
        "role": {"$in": INSPECTION_ASSIGNEE_ROLES},
        "is_active": True,
    })
    if assignee is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Inspection assignee must be an active administrator or maintenance manager",
        )
    now, actor_id = utc_now(), _actor_id(current_user)
    changes = {
        "assigned_to": assignee_id,
        "assigned_by": actor_id,
        "assigned_at": now,
    }
    validate_inspection_transition("pending", "assigned", changes)
    return await _transition(inspection_id, "pending", "assigned", changes)


async def start_inspection(
    inspection_id: str, data: dict[str, Any], current_user: dict[str, Any]
) -> dict[str, Any]:
    actor_id, now = _actor_id(current_user), utc_now()
    changes = {"started_by": actor_id, "started_at": now}
    if data.get("notes"):
        changes["start_notes"] = str(data["notes"]).strip()
    validate_inspection_transition("assigned", "in_progress", changes)
    return await _transition(
        inspection_id,
        "assigned",
        "in_progress",
        changes,
        extra_filter={"assigned_to": actor_id},
    )


async def save_inspection_draft(
    inspection_id: str, data: dict[str, Any], current_user: dict[str, Any]
) -> dict[str, Any]:
    actor_id, now = _actor_id(current_user), utc_now()
    changes: dict[str, Any] = {
        "draft_saved_by": actor_id,
        "draft_saved_at": now,
        "updated_at": now,
    }
    if "checklist" in data:
        changes["draft_checklist"] = list(data["checklist"] or [])
    if "summary" in data:
        changes["draft_summary"] = data["summary"]

    oid = _oid(inspection_id, "inspection ID")
    row = await _db()[INSPECTION_COLLECTION].find_one_and_update(
        {
            "_id": oid,
            "status": "in_progress",
            "is_active": True,
            "assigned_to": actor_id,
        },
        {"$set": changes},
        return_document=ReturnDocument.AFTER,
    )
    if row is None:
        existing = await _db()[INSPECTION_COLLECTION].find_one({"_id": oid})
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Drafts can only be saved by the assignee while the inspection is active and in progress",
        )
    return _public(row) or {}


async def complete_inspection(
    inspection_id: str, data: dict[str, Any], current_user: dict[str, Any]
) -> dict[str, Any]:
    actor_id, now = _actor_id(current_user), utc_now()
    completed = {"completed_by": actor_id, "completed_at": now}
    decision_pending = {"decision_pending_by": actor_id, "decision_pending_at": now}
    validate_inspection_transition("in_progress", "completed", completed)
    validate_inspection_transition("completed", "decision_pending", decision_pending)
    changes = {
        **completed,
        **decision_pending,
        "checklist": list(data["checklist"]),
        "summary": data["summary"],
        "draft_checklist": [],
        "draft_summary": None,
        "draft_saved_by": None,
        "draft_saved_at": None,
        "is_active": True,
    }
    return await _transition(
        inspection_id,
        "in_progress",
        "decision_pending",
        changes,
        extra_filter={"assigned_to": actor_id},
    )


async def cancel_inspection(
    inspection_id: str, data: dict[str, Any], current_user: dict[str, Any]
) -> dict[str, Any]:
    actor_id, now = _actor_id(current_user), utc_now()
    changes = {
        "cancelled_by": actor_id,
        "cancelled_at": now,
        "cancellation_reason": str(data["reason"]).strip(),
        "is_active": False,
    }
    for source_status in CANCELLABLE_STATUSES:
        validate_inspection_transition(source_status, "cancelled", changes)
    cancelled = await _transition(
        inspection_id,
        {"$in": CANCELLABLE_STATUSES},
        "cancelled",
        changes,
    )
    if cancelled.get("inspection_type") == "commissioning":
        await _db()[VEHICLE_COLLECTION].update_one(
            {"_id": _oid(cancelled["vehicle_id"], "vehicle ID"), "commissioning_status": "pending"},
            {"$set": {"commissioning_status": "not_started", "updated_at": now}},
        )
    return cancelled


async def _matching_review(inspection: dict[str, Any]) -> dict[str, Any] | None:
    return await _db()[PREDICTION_REVIEW_COLLECTION].find_one({
        "vehicle_id": inspection["vehicle_id"],
        "feature_hash": inspection["feature_hash"],
        "status": {"$in": ["pending", "confirmed"]},
    })


async def _set_review_resolution(
    review: dict[str, Any], resolution: str, notes: str, actor_id: ObjectId, now: datetime,
) -> dict[str, Any]:
    update = {
        "status": resolution,
        "resolution": resolution,
        "notes": notes,
        "resolved_by": actor_id,
        "resolved_at": now,
        "updated_at": now,
    }
    row = await _db()[PREDICTION_REVIEW_COLLECTION].find_one_and_update(
        {"_id": review["_id"], "status": review["status"]},
        {"$set": update},
        return_document=ReturnDocument.AFTER,
    )
    if row is None:
        row = await _db()[PREDICTION_REVIEW_COLLECTION].find_one({"_id": review["_id"]})
        if row is None or row.get("status") != resolution:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Engineering review changed concurrently")
    hold = resolution == "confirmed"
    await _db()[PREDICTION_COLLECTION].update_many(
        {"vehicle_id": review["vehicle_id"], "feature_hash": review["feature_hash"]},
        {"$set": {
            "review_status": resolution,
            "dispatch_hold": hold,
            "policy_decision": "hold_for_maintenance" if hold else "operation_allowed",
        }},
    )
    return row


async def _can_restore_after_inspection(
    vehicle_id: ObjectId,
    inspection_id: ObjectId,
    *,
    allow_inactive: bool = False,
) -> bool:
    vehicle = await _db()[VEHICLE_COLLECTION].find_one({"_id": vehicle_id})
    if vehicle is None or vehicle.get("status") == "retired" or vehicle.get("health_status") == "critical":
        return False
    if vehicle.get("status") == "inactive" and not allow_inactive:
        return False
    if await _db()[PREDICTION_REVIEW_COLLECTION].find_one({
        "vehicle_id": vehicle_id, "status": {"$in": ["pending", "confirmed"]},
    }):
        return False
    latest = await _db()[PREDICTION_COLLECTION].find_one({"vehicle_id": vehicle_id}, sort=[("created_at", -1)])
    if latest and latest.get("dispatch_hold") is True:
        return False
    if await _db()[INSPECTION_COLLECTION].find_one({
        "vehicle_id": vehicle_id, "is_active": True, "_id": {"$ne": inspection_id},
    }):
        return False
    if await _db()[MAINTENANCE_COLLECTION].find_one({
        "vehicle_id": vehicle_id,
        "$or": [
            {"work_order_status": {"$in": ["planned", "approved", "in_progress"]}},
            {
                "work_order_status": {"$exists": False},
                "status": {"$in": ["scheduled", "in_progress"]},
            },
        ],
    }):
        return False
    return True


async def decide_inspection(
    inspection_id: str, data: dict[str, Any], current_user: dict[str, Any]
) -> dict[str, Any]:
    inspection_oid = _oid(inspection_id, "inspection ID")
    inspection = await _db()[INSPECTION_COLLECTION].find_one({"_id": inspection_oid})
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    decision = str(data.get("decision") or "")
    if decision not in {"maintenance_required", "returned_to_service"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid inspection decision")
    notes = str(data.get("notes") or "").strip()
    if not notes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Decision notes are required")
    actor_id, now = _actor_id(current_user), utc_now()
    review = await _matching_review(inspection)

    if decision == "returned_to_service":
        if (
            inspection.get("status") == "returned_to_service"
            and inspection.get("is_active") is False
            and inspection.get("decision") == decision
            and inspection.get("decision_notes") == notes
        ):
            return {"inspection": _public(inspection) or {}, "work_order": None}
        if inspection.get("status") != "decision_pending" or inspection.get("is_active") is not True:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inspection is not awaiting a decision")
        confirmed_review = await _db()[PREDICTION_REVIEW_COLLECTION].find_one({
            "vehicle_id": inspection["vehicle_id"], "status": "confirmed",
        })
        if confirmed_review is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A confirmed engineering issue requires completed maintenance",
            )
        if review and review.get("status") == "pending":
            await _set_review_resolution(review, "cleared", notes, actor_id, now)
        changes = {
            "decision": decision,
            "decision_notes": notes,
            "decided_by": actor_id,
            "decided_at": now,
            "is_active": False,
        }
        validate_inspection_transition("decision_pending", decision, changes)
        updated = await _transition(inspection_id, "decision_pending", decision, changes)
        if inspection.get("inspection_type") == "commissioning":
            can_activate = await _can_restore_after_inspection(
                inspection["vehicle_id"], inspection_oid, allow_inactive=True
            )
            await _db()[VEHICLE_COLLECTION].update_one(
                {"_id": inspection["vehicle_id"], "status": {"$ne": "retired"}},
                {"$set": {
                    **({"status": "active"} if can_activate else {}),
                    "commissioning_status": "passed",
                    "updated_at": now,
                }},
            )
        elif await _can_restore_after_inspection(inspection["vehicle_id"], inspection_oid):
            await _db()[VEHICLE_COLLECTION].update_one(
                {"_id": inspection["vehicle_id"], "status": {"$in": ["active", "under_maintenance"]}},
                {"$set": {"status": "active", "updated_at": now}},
            )
        return {"inspection": updated, "work_order": None}

    if inspection.get("status") not in {"decision_pending", "maintenance_required"} or inspection.get("is_active") is not True:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inspection cannot create a maintenance order")
    if review and review.get("status") == "pending":
        review = await _set_review_resolution(review, "confirmed", notes, actor_id, now)

    if inspection.get("status") == "decision_pending":
        claim_changes = {
            "decision": decision,
            "decision_notes": notes,
            "decided_by": actor_id,
            "decided_at": now,
            "is_active": True,
        }
        validate_inspection_transition("decision_pending", decision, claim_changes)
        claimed = await _db()[INSPECTION_COLLECTION].find_one_and_update(
            {"_id": inspection_oid, "status": "decision_pending", "is_active": True},
            {"$set": {**claim_changes, "status": decision, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if claimed is None:
            claimed = await _db()[INSPECTION_COLLECTION].find_one({"_id": inspection_oid})
            if claimed is None or claimed.get("status") != "maintenance_required" or claimed.get("is_active") is not True:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inspection decision changed concurrently")
        inspection = claimed

    from app.services.maintenance_service import create_inspection_work_order

    work_order = await create_inspection_work_order(inspection, data, review, current_user)
    work_order_oid = _oid(work_order["id"], "work-order ID")
    if review:
        await _db()[PREDICTION_REVIEW_COLLECTION].update_one(
            {"_id": review["_id"], "status": "confirmed"},
            {"$set": {"linked_maintenance_record_id": work_order_oid, "updated_at": now}},
        )
    row = await _db()[INSPECTION_COLLECTION].find_one_and_update(
        {"_id": inspection_oid, "status": "maintenance_required", "is_active": True},
        {"$set": {"work_order_id": work_order_oid, "updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inspection work-order link changed concurrently")
    updated = _public(row) or {}
    vehicle_update: dict[str, Any] = {"status": "under_maintenance", "updated_at": now}
    if inspection.get("inspection_type") == "commissioning":
        vehicle_update["commissioning_status"] = "failed"
    await _db()[VEHICLE_COLLECTION].update_one(
        {"_id": inspection["vehicle_id"], "status": {"$ne": "retired"}},
        {"$set": vehicle_update},
    )
    return {"inspection": updated, "work_order": work_order}
