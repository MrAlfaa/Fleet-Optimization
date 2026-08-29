from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.models.user_model import utc_now
from app.utils.object_id import serialize_mongo_document


INSPECTION_COLLECTION = "vehicle_maintenance_inspections"

INSPECTION_STATUSES = {
    "pending",
    "assigned",
    "in_progress",
    "completed",
    "decision_pending",
    "maintenance_required",
    "returned_to_service",
    "cancelled",
}
INSPECTION_PRIORITIES = {"low", "medium", "high", "critical"}
INSPECTION_DECISIONS = {"maintenance_required", "returned_to_service"}
INSPECTION_CHECK_OUTCOMES = {"passed", "failed", "not_applicable"}
INSPECTION_TERMINAL_STATUSES = {"maintenance_required", "returned_to_service", "cancelled"}

WORK_ORDER_STATUSES = {"planned", "approved", "in_progress", "completed", "cancelled"}
WORK_ORDER_TERMINAL_STATUSES = {"completed", "cancelled"}

INSPECTION_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"assigned", "cancelled"},
    "assigned": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": {"decision_pending"},
    "decision_pending": {"maintenance_required", "returned_to_service"},
    "maintenance_required": set(),
    "returned_to_service": set(),
    "cancelled": set(),
}

WORK_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "planned": {"approved", "cancelled"},
    "approved": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

_INSPECTION_REQUIRED_TRANSITION_FIELDS: dict[str, tuple[str, ...]] = {
    "assigned": ("assigned_to", "assigned_by", "assigned_at"),
    "in_progress": ("started_by", "started_at"),
    "completed": ("completed_by", "completed_at"),
    "decision_pending": ("decision_pending_by", "decision_pending_at"),
    "maintenance_required": ("decision", "decided_by", "decided_at"),
    "returned_to_service": ("decision", "decided_by", "decided_at"),
    "cancelled": ("cancelled_by", "cancelled_at", "cancellation_reason"),
}

_WORK_ORDER_REQUIRED_TRANSITION_FIELDS: dict[str, tuple[str, ...]] = {
    "approved": ("approved_by", "approved_at"),
    "in_progress": ("started_by", "started_at"),
    "completed": ("completed_by", "completed_at"),
    "cancelled": ("cancelled_by", "cancelled_at", "cancellation_reason"),
}

INSPECTION_INDEXES: tuple[dict[str, Any], ...] = (
    {
        "keys": [("vehicle_id", ASCENDING), ("status", ASCENDING)],
        "name": "inspection_vehicle_status",
    },
    {
        "keys": [("status", ASCENDING), ("priority", ASCENDING), ("created_at", ASCENDING)],
        "name": "inspection_queue",
    },
    {
        "keys": [("assigned_to", ASCENDING), ("status", ASCENDING)],
        "name": "inspection_assignee_status",
    },
    {
        "keys": [("assessment_id", ASCENDING), ("feature_hash", ASCENDING)],
        "name": "inspection_assessment_feature",
    },
    {
        "keys": [("vehicle_id", ASCENDING)],
        "name": "unique_active_vehicle_inspection",
        "unique": True,
        "partialFilterExpression": {"is_active": True},
    },
    {
        "keys": [("created_at", DESCENDING)],
        "name": "inspection_created_at",
    },
)

WORK_ORDER_INDEXES: tuple[dict[str, Any], ...] = (
    {"keys": [("work_order_status", ASCENDING)], "name": "work_order_status"},
    {
        "keys": [("inspection_id", ASCENDING)],
        "name": "unique_inspection_work_order",
        "unique": True,
        "partialFilterExpression": {
            "inspection_id": {"$type": "objectId"},
            "work_order_status": {"$in": ["planned", "approved", "in_progress"]},
        },
    },
    {"keys": [("assessment_id", ASCENDING)], "name": "work_order_assessment"},
)


def _require_transition_fields(target: str, changes: dict[str, Any], required: tuple[str, ...]) -> None:
    for field in required:
        value = changes.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"{field} is required for transition to {target}")
        if field.endswith("_at") and not isinstance(value, datetime):
            raise ValueError(f"{field} must be a datetime")


def validate_inspection_transition(current: str, target: str, changes: dict[str, Any]) -> None:
    if current not in INSPECTION_STATUSES or target not in INSPECTION_STATUSES:
        raise ValueError(f"Invalid inspection transition from {current} to {target}")
    if target not in INSPECTION_TRANSITIONS[current]:
        raise ValueError(f"Invalid inspection transition from {current} to {target}")
    _require_transition_fields(target, changes, _INSPECTION_REQUIRED_TRANSITION_FIELDS[target])
    if target in INSPECTION_DECISIONS and changes.get("decision") != target:
        raise ValueError(f"decision must match transition target {target}")


def validate_work_order_transition(current: str, target: str, changes: dict[str, Any]) -> None:
    if current not in WORK_ORDER_STATUSES or target not in WORK_ORDER_STATUSES:
        raise ValueError(f"Invalid work-order transition from {current} to {target}")
    if target not in WORK_ORDER_TRANSITIONS[current]:
        raise ValueError(f"Invalid work-order transition from {current} to {target}")
    _require_transition_fields(target, changes, _WORK_ORDER_REQUIRED_TRANSITION_FIELDS[target])


def build_inspection_document(
    data: dict[str, Any], created_by: Any, *, now: datetime | None = None
) -> dict[str, Any]:
    created_at = now or utc_now()
    return {
        "vehicle_id": data["vehicle_id"],
        "inspection_type": data.get("inspection_type", "risk_assessment"),
        "assessment_id": data.get("assessment_id"),
        "feature_hash": data["feature_hash"],
        "status": "pending",
        "is_active": True,
        "priority": data.get("priority", "medium"),
        "inspection_areas": list(data.get("inspection_areas") or []),
        "notes": data.get("notes"),
        "checklist": [],
        "summary": None,
        "draft_checklist": [],
        "draft_summary": None,
        "draft_saved_by": None,
        "draft_saved_at": None,
        "assigned_to": None,
        "assigned_by": None,
        "assigned_at": None,
        "started_by": None,
        "started_at": None,
        "completed_by": None,
        "completed_at": None,
        "decision_pending_by": None,
        "decision_pending_at": None,
        "decision": None,
        "decision_notes": None,
        "decided_by": None,
        "decided_at": None,
        "work_order_id": None,
        "cancelled_by": None,
        "cancelled_at": None,
        "cancellation_reason": None,
        "created_by": created_by,
        "created_at": created_at,
        "updated_at": created_at,
    }


def safe_inspection_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    return serialize_mongo_document(document)


async def ensure_inspection_indexes() -> None:
    db = get_database()
    if db is None:
        return
    try:
        collection = db[INSPECTION_COLLECTION]
        for specification in INSPECTION_INDEXES:
            options = {key: value for key, value in specification.items() if key != "keys"}
            await collection.create_index(specification["keys"], **options)
    except PyMongoError:
        return
