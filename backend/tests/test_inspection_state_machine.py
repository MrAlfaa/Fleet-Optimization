from datetime import datetime, timezone

import pytest
from bson import ObjectId
from pydantic import ValidationError

from app.models.inspection_model import (
    INSPECTION_INDEXES,
    INSPECTION_STATUSES,
    WORK_ORDER_INDEXES,
    WORK_ORDER_STATUSES,
    build_inspection_document,
    safe_inspection_document,
    validate_inspection_transition,
    validate_work_order_transition,
)
from app.models.maintenance_model import build_maintenance_document
from app.schemas.inspection_schema import (
    InspectionChecklistItem,
    InspectionCompleteRequest,
    InspectionCreateRequest,
    InspectionDecisionRequest,
    InspectionResponse,
)


NOW = datetime(2026, 8, 27, 9, 30, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("domain", "current", "target"),
    [
        ("inspection", "pending", "assigned"),
        ("inspection", "assigned", "in_progress"),
        ("inspection", "in_progress", "completed"),
        ("inspection", "completed", "decision_pending"),
        ("inspection", "decision_pending", "maintenance_required"),
        ("inspection", "decision_pending", "returned_to_service"),
        ("inspection", "pending", "cancelled"),
        ("inspection", "assigned", "cancelled"),
        ("inspection", "in_progress", "cancelled"),
        ("work_order", "planned", "approved"),
        ("work_order", "approved", "in_progress"),
        ("work_order", "in_progress", "completed"),
        ("work_order", "planned", "cancelled"),
    ],
)
def test_state_machines_accept_only_frozen_forward_transitions(domain: str, current: str, target: str) -> None:
    actor_changes = {
        "assigned_to": ObjectId(), "assigned_by": ObjectId(), "assigned_at": NOW,
        "started_by": ObjectId(), "started_at": NOW,
        "completed_by": ObjectId(), "completed_at": NOW,
        "decision_pending_by": ObjectId(), "decision_pending_at": NOW,
        "decision": target if target in {"maintenance_required", "returned_to_service"} else None,
        "decided_by": ObjectId(), "decided_at": NOW,
        "cancelled_by": ObjectId(), "cancelled_at": NOW, "cancellation_reason": "No longer required",
        "approved_by": ObjectId(), "approved_at": NOW,
    }
    if domain == "work_order":
        validate_work_order_transition(current, target, actor_changes)
    else:
        validate_inspection_transition(current, target, actor_changes)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("pending", "in_progress"),
        ("assigned", "completed"),
        ("in_progress", "maintenance_required"),
        ("completed", "returned_to_service"),
        ("returned_to_service", "pending"),
        ("maintenance_required", "cancelled"),
        ("cancelled", "pending"),
    ],
)
def test_inspection_state_machine_rejects_skips_and_terminal_mutation(current: str, target: str) -> None:
    with pytest.raises(ValueError, match="transition"):
        validate_inspection_transition(current, target, {})


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("planned", "completed"),
        ("approved", "completed"),
        ("completed", "in_progress"),
        ("cancelled", "planned"),
    ],
)
def test_work_order_state_machine_rejects_skips_and_terminal_mutation(current: str, target: str) -> None:
    with pytest.raises(ValueError, match="transition"):
        validate_work_order_transition(current, target, {})


@pytest.mark.parametrize(
    ("current", "target", "changes", "missing_field"),
    [
        ("pending", "assigned", {"assigned_to": ObjectId(), "assigned_at": NOW}, "assigned_by"),
        ("assigned", "in_progress", {"started_at": NOW}, "started_by"),
        ("in_progress", "completed", {"completed_by": ObjectId()}, "completed_at"),
        ("decision_pending", "returned_to_service", {"decision": "returned_to_service", "decided_at": NOW}, "decided_by"),
        ("pending", "cancelled", {"cancelled_by": ObjectId(), "cancelled_at": NOW}, "cancellation_reason"),
    ],
)
def test_inspection_transitions_require_actor_and_timestamp_evidence(
    current: str, target: str, changes: dict, missing_field: str
) -> None:
    with pytest.raises(ValueError, match=missing_field):
        validate_inspection_transition(current, target, changes)


def test_checklist_requires_unique_items_and_a_remark_for_every_failed_check() -> None:
    with pytest.raises(ValidationError, match="remark"):
        InspectionCompleteRequest(
            checklist=[
                InspectionChecklistItem(
                    key="brakes", label="Brake condition", outcome="failed", remark=None
                )
            ],
            summary="Brake inspection completed",
        )

    with pytest.raises(ValidationError, match="unique"):
        InspectionCompleteRequest(
            checklist=[
                InspectionChecklistItem(key="tires", label="Front tires", outcome="passed"),
                InspectionChecklistItem(key="tires", label="Rear tires", outcome="passed"),
            ],
            summary="Tire inspection completed",
        )


def test_checklist_accepts_completed_structured_results() -> None:
    payload = InspectionCompleteRequest(
        checklist=[
            InspectionChecklistItem(key="brakes", label="Brake condition", outcome="passed"),
            InspectionChecklistItem(
                key="tires", label="Tire condition", outcome="failed", remark="Rear-left tire worn"
            ),
            InspectionChecklistItem(key="charging", label="Charging system", outcome="not_applicable"),
        ],
        summary="Vehicle requires a tire repair decision.",
    )
    assert payload.checklist[1].remark == "Rear-left tire worn"


def test_creation_and_decision_schemas_reject_uncontrolled_values() -> None:
    with pytest.raises(ValidationError):
        InspectionCreateRequest(
            vehicle_id=str(ObjectId()), assessment_id=str(ObjectId()), feature_hash="abc123",
            priority="urgent",
        )
    with pytest.raises(ValidationError):
        InspectionDecisionRequest(decision="defer", notes="Review later")
    with pytest.raises(ValidationError, match="notes"):
        InspectionDecisionRequest(decision="maintenance_required", notes="  ")


def test_inspection_builder_and_serializer_preserve_audit_identity() -> None:
    vehicle_id, assessment_id, actor_id = ObjectId(), ObjectId(), ObjectId()
    document = build_inspection_document(
        {
            "vehicle_id": vehicle_id,
            "assessment_id": assessment_id,
            "feature_hash": "feature-hash-v1",
            "priority": "high",
            "inspection_areas": ["braking", "tires"],
        },
        actor_id,
        now=NOW,
    )
    document["_id"] = ObjectId()
    serialized = safe_inspection_document(document)

    assert document["status"] == "pending"
    assert document["is_active"] is True
    assert document["created_by"] == actor_id
    assert document["created_at"] == NOW
    assert serialized is not None
    assert serialized["vehicle_id"] == str(vehicle_id)
    assert serialized["assessment_id"] == str(assessment_id)
    assert serialized["id"] == str(document["_id"])


def test_inspection_response_defaults_to_active() -> None:
    response = InspectionResponse(
        id=str(ObjectId()),
        vehicle_id=str(ObjectId()),
        assessment_id=str(ObjectId()),
        feature_hash="feature-hash-v1",
        status="pending",
        priority="high",
        created_by=str(ObjectId()),
        created_at=NOW,
        updated_at=NOW,
    )
    assert response.is_active is True


def test_indexes_cover_active_vehicle_queue_and_linked_work_order_identity() -> None:
    inspection_names = {spec["name"] for spec in INSPECTION_INDEXES}
    work_order_names = {spec["name"] for spec in WORK_ORDER_INDEXES}
    assert {"inspection_vehicle_status", "inspection_queue", "unique_active_vehicle_inspection"} <= inspection_names
    assert {"work_order_status", "unique_inspection_work_order"} <= work_order_names

    active_index = next(
        specification
        for specification in INSPECTION_INDEXES
        if specification["name"] == "unique_active_vehicle_inspection"
    )
    assert active_index["unique"] is True
    assert active_index["partialFilterExpression"] == {"is_active": True}


def test_maintenance_document_supports_frozen_work_order_contract() -> None:
    inspection_id, assessment_id, actor_id = ObjectId(), ObjectId(), ObjectId()
    document = build_maintenance_document(
        {
            "vehicle_id": ObjectId(),
            "part_name": "Brake Pads",
            "maintenance_type": "corrective",
            "maintenance_system": "braking",
            "event_kind": "corrective_repair",
            "issue_type": "Excessive wear",
            "service_date": NOW,
            "mileage_at_service": 42_000,
            "work_order_status": "planned",
            "inspection_id": inspection_id,
            "assessment_id": assessment_id,
            "estimated_cost": 25_000,
        },
        actor_id,
    )
    assert document["work_order_status"] == "planned"
    assert document["inspection_id"] == inspection_id
    assert document["assessment_id"] == assessment_id
    assert document["estimated_cost"] == 25_000
    assert document["actual_cost"] is None
    assert document["started_at"] is None
    assert document["completed_at"] is None


def test_frozen_status_sets_are_complete() -> None:
    assert INSPECTION_STATUSES == {
        "pending", "assigned", "in_progress", "completed", "decision_pending",
        "maintenance_required", "returned_to_service", "cancelled",
    }
    assert WORK_ORDER_STATUSES == {"planned", "approved", "in_progress", "completed", "cancelled"}
