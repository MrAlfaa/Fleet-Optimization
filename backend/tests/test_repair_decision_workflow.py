from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError
from pymongo import ReturnDocument

from app.models.inspection_model import INSPECTION_COLLECTION, WORK_ORDER_INDEXES
from app.models.maintenance_intelligence_model import PREDICTION_REVIEW_COLLECTION
from app.models.maintenance_model import MAINTENANCE_COLLECTION
from app.models import maintenance_model
from app.models.predictive_model import PREDICTION_COLLECTION
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.schemas.inspection_schema import InspectionDecisionRequest
from app.schemas.maintenance_schema import (
    MaintenanceCancelRequest,
    MaintenanceCompleteRequest,
)
from app.services import inspection_service, maintenance_service


NOW = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)


def _matches(row: dict, query: dict) -> bool:
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches(row, branch) for branch in expected):
                return False
            continue
        actual = row.get(key)
        if isinstance(expected, dict):
            if "$in" in expected and actual not in expected["$in"]:
                return False
            if "$ne" in expected and actual == expected["$ne"]:
                return False
            if "$exists" in expected and (key in row) is not expected["$exists"]:
                return False
        elif actual != expected:
            return False
    return True


class _Cursor:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def sort(self, *args, **kwargs):
        return self

    def skip(self, count: int):
        self.rows = self.rows[count:]
        return self

    def limit(self, count: int):
        self.rows = self.rows[:count]
        return self

    async def to_list(self, length: int):
        return deepcopy(self.rows[:length])


class _Collection:
    def __init__(self, rows: list[dict] | None = None):
        self.rows = deepcopy(rows or [])
        self.atomic_calls: list[tuple[dict, dict]] = []

    async def find_one(self, query: dict, **kwargs):
        return next((deepcopy(row) for row in self.rows if _matches(row, query)), None)

    def find(self, query: dict):
        return _Cursor([deepcopy(row) for row in self.rows if _matches(row, query)])

    async def insert_one(self, document: dict):
        row = deepcopy(document)
        row["_id"] = ObjectId()
        self.rows.append(row)
        return SimpleNamespace(inserted_id=row["_id"])

    async def find_one_and_update(self, query: dict, update: dict, return_document=None):
        self.atomic_calls.append((deepcopy(query), deepcopy(update)))
        for index, row in enumerate(self.rows):
            if _matches(row, query):
                before = deepcopy(row)
                row.update(deepcopy(update.get("$set", {})))
                self.rows[index] = row
                return deepcopy(row if return_document == ReturnDocument.AFTER else before)
        return None

    async def update_one(self, query: dict, update: dict):
        row = await self.find_one_and_update(query, update, ReturnDocument.AFTER)
        return SimpleNamespace(matched_count=int(row is not None), modified_count=int(row is not None))

    async def update_many(self, query: dict, update: dict):
        count = 0
        for index, row in enumerate(self.rows):
            if _matches(row, query):
                row.update(deepcopy(update.get("$set", {})))
                self.rows[index] = row
                count += 1
        return SimpleNamespace(matched_count=count, modified_count=count)

    async def delete_one(self, query: dict):
        for index, row in enumerate(self.rows):
            if _matches(row, query):
                self.rows.pop(index)
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    async def count_documents(self, query: dict):
        return sum(1 for row in self.rows if _matches(row, query))


def _actor() -> dict:
    return {"id": str(ObjectId()), "role": "maintenance_manager"}


def _base_records(*, review_status: str | None = "pending") -> tuple[dict, dict]:
    vehicle_id, assessment_id, inspection_id = ObjectId(), ObjectId(), ObjectId()
    inspection = {
        "_id": inspection_id,
        "vehicle_id": vehicle_id,
        "assessment_id": assessment_id,
        "feature_hash": "feature-v3",
        "status": "decision_pending",
        "is_active": True,
        "priority": "high",
        "inspection_areas": ["braking"],
        "created_by": ObjectId(),
        "created_at": NOW,
        "updated_at": NOW,
    }
    db = {
        INSPECTION_COLLECTION: _Collection([inspection]),
        MAINTENANCE_COLLECTION: _Collection(),
        VEHICLE_COLLECTION: _Collection([{
            "_id": vehicle_id,
            "status": "active",
            "health_status": "healthy",
            "current_mileage": 48_200,
        }]),
        PREDICTION_COLLECTION: _Collection([{
            "_id": assessment_id,
            "vehicle_id": vehicle_id,
            "feature_hash": "feature-v3",
            "risk_level": "high",
            "dispatch_hold": True,
        }]),
        PREDICTION_REVIEW_COLLECTION: _Collection([] if review_status is None else [{
            "_id": ObjectId(),
            "vehicle_id": vehicle_id,
            "prediction_id": assessment_id,
            "feature_hash": "feature-v3",
            "status": review_status,
        }]),
        "alerts": _Collection(),
        "vehicle_parts": _Collection(),
    }
    return db, inspection


def test_decision_schema_requires_branch_fields_and_notes() -> None:
    with pytest.raises(ValidationError):
        InspectionDecisionRequest(decision="returned_to_service", notes=" ")
    with pytest.raises(ValidationError):
        InspectionDecisionRequest(decision="repair_later", notes="Checked")
    with pytest.raises(ValidationError, match="maintenance_system"):
        InspectionDecisionRequest(decision="maintenance_required", notes="Brake fault")

    payload = InspectionDecisionRequest(
        decision="maintenance_required",
        notes="Brake pads require replacement",
        maintenance_system="braking",
        issue_type="Brake wear beyond limit",
        priority="high",
        estimated_cost=42_500,
    )
    assert payload.maintenance_system == "braking"


def test_work_order_index_allows_cancelled_history_and_one_active_replacement() -> None:
    index = next(item for item in WORK_ORDER_INDEXES if item["name"] == "unique_inspection_work_order")
    assert index["partialFilterExpression"] == {
        "inspection_id": {"$type": "objectId"},
        "work_order_status": {"$in": ["planned", "approved", "in_progress"]},
    }


@pytest.mark.asyncio
async def test_index_setup_replaces_legacy_all_history_unique_index(monkeypatch) -> None:
    class IndexCollection:
        def __init__(self):
            self.dropped: list[str] = []
            self.created: list[tuple[list, dict]] = []

        async def index_information(self):
            return {
                "unique_inspection_work_order": {
                    "partialFilterExpression": {"inspection_id": {"$type": "objectId"}}
                }
            }

        async def drop_index(self, name: str):
            self.dropped.append(name)

        async def create_index(self, keys, **options):
            self.created.append((keys, options))

    collection = IndexCollection()
    monkeypatch.setattr(maintenance_model, "get_database", lambda: {MAINTENANCE_COLLECTION: collection})

    await maintenance_model.ensure_maintenance_indexes()

    assert collection.dropped == ["unique_inspection_work_order"]
    recreated = next(options for _, options in collection.created if options.get("name") == "unique_inspection_work_order")
    assert recreated["partialFilterExpression"]["work_order_status"]["$in"] == [
        "planned", "approved", "in_progress"
    ]


@pytest.mark.asyncio
async def test_maintenance_required_confirms_review_creates_one_order_and_holds_vehicle(monkeypatch) -> None:
    db, inspection = _base_records()
    monkeypatch.setattr(inspection_service, "_db", lambda: db)
    monkeypatch.setattr(maintenance_service, "_db", lambda: db)
    monkeypatch.setattr(maintenance_service, "get_maintenance_collection", lambda: db[MAINTENANCE_COLLECTION])
    monkeypatch.setattr(inspection_service, "utc_now", lambda: NOW)
    monkeypatch.setattr(maintenance_service, "utc_now", lambda: NOW)
    monkeypatch.setattr(maintenance_service, "create_maintenance_alert", lambda *args, **kwargs: _noop())

    payload = {
        "decision": "maintenance_required",
        "notes": "Brake pads require replacement",
        "maintenance_system": "braking",
        "issue_type": "Brake wear beyond limit",
        "priority": "high",
        "estimated_cost": 42_500,
    }
    first = await inspection_service.decide_inspection(str(inspection["_id"]), payload, _actor())
    second = await inspection_service.decide_inspection(str(inspection["_id"]), payload, _actor())

    assert first["work_order"]["id"] == second["work_order"]["id"]
    assert first["inspection"]["status"] == "maintenance_required"
    assert first["inspection"]["is_active"] is True
    assert len(db[MAINTENANCE_COLLECTION].rows) == 1
    order = db[MAINTENANCE_COLLECTION].rows[0]
    assert order["inspection_id"] == inspection["_id"]
    assert order["assessment_id"] == inspection["assessment_id"]
    assert order["work_order_status"] == "planned"
    assert order["estimated_cost"] == 42_500
    assert db[VEHICLE_COLLECTION].rows[0]["status"] == "under_maintenance"
    assert db[PREDICTION_REVIEW_COLLECTION].rows[0]["status"] == "confirmed"
    assert db[PREDICTION_REVIEW_COLLECTION].rows[0]["linked_maintenance_record_id"] == order["_id"]


@pytest.mark.asyncio
async def test_maintenance_required_reuses_matching_open_vehicle_work_order(monkeypatch) -> None:
    db, inspection = _base_records(review_status=None)
    existing_order_id = ObjectId()
    db[MAINTENANCE_COLLECTION].rows.append({
        "_id": existing_order_id,
        "vehicle_id": inspection["vehicle_id"],
        "part_id": None,
        "part_name": "Front brake pads",
        "maintenance_type": "preventive",
        "maintenance_system": "braking",
        "event_kind": "scheduled_service",
        "issue_type": "Scheduled front brake service",
        "service_date": NOW,
        "mileage_at_service": 48_200.0,
        "technician_name": "Nimal Perera",
        "service_center": None,
        "cost": 18_500.0,
        "status": "scheduled",
        "priority": "medium",
        "notes": "Existing planned braking work",
        "prediction_review_id": None,
        "inspection_id": None,
        "assessment_id": None,
        "work_order_status": "planned",
        "estimated_cost": 18_500.0,
        "actual_cost": None,
        "record_source": "operational",
        "created_by": ObjectId(),
        "created_at": NOW,
        "updated_at": NOW,
    })
    monkeypatch.setattr(inspection_service, "_db", lambda: db)
    monkeypatch.setattr(maintenance_service, "_db", lambda: db)
    monkeypatch.setattr(maintenance_service, "get_maintenance_collection", lambda: db[MAINTENANCE_COLLECTION])
    monkeypatch.setattr(inspection_service, "utc_now", lambda: NOW)
    monkeypatch.setattr(maintenance_service, "utc_now", lambda: NOW)

    result = await inspection_service.decide_inspection(
        str(inspection["_id"]),
        {
            "decision": "maintenance_required",
            "notes": "Brake wear confirmed during inspection",
            "maintenance_system": "braking",
            "issue_type": "Brake wear beyond limit",
            "priority": "high",
            "estimated_cost": 42_500,
        },
        _actor(),
    )

    assert len(db[MAINTENANCE_COLLECTION].rows) == 1
    assert result["work_order"]["id"] == str(existing_order_id)
    linked = db[MAINTENANCE_COLLECTION].rows[0]
    assert linked["inspection_id"] == inspection["_id"]
    assert linked["assessment_id"] == inspection["assessment_id"]
    assert linked["maintenance_type"] == "preventive"
    assert linked["issue_type"] == "Scheduled front brake service"
    assert result["inspection"]["work_order_id"] == str(existing_order_id)


@pytest.mark.asyncio
async def test_return_to_service_rejects_confirmed_issue_and_clears_pending_review(monkeypatch) -> None:
    confirmed_db, inspection = _base_records(review_status="confirmed")
    monkeypatch.setattr(inspection_service, "_db", lambda: confirmed_db)
    with pytest.raises(HTTPException, match="confirmed") as blocked:
        await inspection_service.decide_inspection(
            str(inspection["_id"]), {"decision": "returned_to_service", "notes": "No defect found"}, _actor()
        )
    assert blocked.value.status_code == 409

    db, inspection = _base_records(review_status="pending")
    monkeypatch.setattr(inspection_service, "_db", lambda: db)
    monkeypatch.setattr(inspection_service, "utc_now", lambda: NOW)
    result = await inspection_service.decide_inspection(
        str(inspection["_id"]), {"decision": "returned_to_service", "notes": "Roadworthy"}, _actor()
    )
    repeated = await inspection_service.decide_inspection(
        str(inspection["_id"]), {"decision": "returned_to_service", "notes": "Roadworthy"}, _actor()
    )
    assert result["inspection"]["status"] == "returned_to_service"
    assert repeated["inspection"]["id"] == result["inspection"]["id"]
    assert result["inspection"]["is_active"] is False
    assert db[PREDICTION_REVIEW_COLLECTION].rows[0]["status"] == "cleared"
    assert db[VEHICLE_COLLECTION].rows[0]["status"] == "active"


@pytest.mark.asyncio
async def test_return_to_service_rejects_any_confirmed_issue_for_vehicle(monkeypatch) -> None:
    db, inspection = _base_records(review_status=None)
    db[PREDICTION_REVIEW_COLLECTION].rows.append({
        "_id": ObjectId(),
        "vehicle_id": inspection["vehicle_id"],
        "prediction_id": ObjectId(),
        "feature_hash": "newer-independent-feature",
        "status": "confirmed",
    })
    monkeypatch.setattr(inspection_service, "_db", lambda: db)

    with pytest.raises(HTTPException, match="confirmed") as blocked:
        await inspection_service.decide_inspection(
            str(inspection["_id"]),
            {"decision": "returned_to_service", "notes": "Inspected vehicle"},
            _actor(),
        )

    assert blocked.value.status_code == 409
    assert db[INSPECTION_COLLECTION].rows[0]["status"] == "decision_pending"


@pytest.mark.asyncio
async def test_return_to_service_does_not_override_independent_legacy_maintenance_blocker(monkeypatch) -> None:
    db, inspection = _base_records(review_status="pending")
    db[VEHICLE_COLLECTION].rows[0]["status"] = "under_maintenance"
    db[MAINTENANCE_COLLECTION].rows.append({
        "_id": ObjectId(),
        "vehicle_id": inspection["vehicle_id"],
        "status": "in_progress",
        "issue_type": "Independent steering repair",
    })
    monkeypatch.setattr(inspection_service, "_db", lambda: db)
    monkeypatch.setattr(inspection_service, "utc_now", lambda: NOW)

    result = await inspection_service.decide_inspection(
        str(inspection["_id"]),
        {"decision": "returned_to_service", "notes": "Inspection item cleared"},
        _actor(),
    )

    assert result["inspection"]["status"] == "returned_to_service"
    assert db[VEHICLE_COLLECTION].rows[0]["status"] == "under_maintenance"


@pytest.mark.asyncio
async def test_work_order_lifecycle_is_atomic_and_terminal_records_are_immutable(monkeypatch) -> None:
    db, inspection = _base_records(review_status=None)
    order_id = ObjectId()
    db[MAINTENANCE_COLLECTION].rows.append({
        "_id": order_id,
        "vehicle_id": inspection["vehicle_id"],
        "inspection_id": inspection["_id"],
        "assessment_id": inspection["assessment_id"],
        "part_name": "Braking",
        "maintenance_type": "corrective",
        "maintenance_system": "braking",
        "issue_type": "Brake wear",
        "service_date": NOW,
        "mileage_at_service": 48_200,
        "priority": "high",
        "status": "scheduled",
        "work_order_status": "planned",
        "created_by": ObjectId(),
        "created_at": NOW,
        "updated_at": NOW,
    })
    monkeypatch.setattr(maintenance_service, "_db", lambda: db)
    monkeypatch.setattr(maintenance_service, "get_maintenance_collection", lambda: db[MAINTENANCE_COLLECTION])
    monkeypatch.setattr(maintenance_service, "utc_now", lambda: NOW)

    approved = await maintenance_service.approve_maintenance_record(str(order_id), _actor())
    approved_retry = await maintenance_service.approve_maintenance_record(str(order_id), _actor())
    started = await maintenance_service.start_maintenance_record(str(order_id), _actor())
    started_retry = await maintenance_service.start_maintenance_record(str(order_id), _actor())
    assert approved["work_order_status"] == "approved"
    assert approved_retry["id"] == approved["id"]
    assert started["work_order_status"] == "in_progress"
    assert started_retry["id"] == started["id"]
    queries = [call[0] for call in db[MAINTENANCE_COLLECTION].atomic_calls]
    assert queries[-2]["work_order_status"] == "planned"
    assert queries[-1]["work_order_status"] == "approved"

    db[MAINTENANCE_COLLECTION].rows[0]["work_order_status"] = "completed"
    db[MAINTENANCE_COLLECTION].rows[0]["status"] = "completed"
    with pytest.raises(HTTPException, match="Terminal"):
        await maintenance_service.update_maintenance_record(str(order_id), {"notes": "overwrite"})


@pytest.mark.asyncio
async def test_cancelled_order_keeps_history_and_allows_replacement(monkeypatch) -> None:
    db, inspection = _base_records(review_status=None)
    cancelled_id = ObjectId()
    db[INSPECTION_COLLECTION].rows[0].update({"status": "maintenance_required", "work_order_id": cancelled_id})
    db[MAINTENANCE_COLLECTION].rows.append({
        "_id": cancelled_id,
        "vehicle_id": inspection["vehicle_id"],
        "inspection_id": inspection["_id"],
        "assessment_id": inspection["assessment_id"],
        "work_order_status": "planned",
        "status": "scheduled",
        "part_name": "Braking",
        "maintenance_system": "braking",
        "issue_type": "Brake wear",
        "priority": "high",
        "service_date": NOW,
        "mileage_at_service": 48_200,
        "created_by": ObjectId(),
        "created_at": NOW,
        "updated_at": NOW,
    })
    monkeypatch.setattr(inspection_service, "_db", lambda: db)
    monkeypatch.setattr(maintenance_service, "_db", lambda: db)
    monkeypatch.setattr(maintenance_service, "get_maintenance_collection", lambda: db[MAINTENANCE_COLLECTION])
    monkeypatch.setattr(inspection_service, "utc_now", lambda: NOW)
    monkeypatch.setattr(maintenance_service, "utc_now", lambda: NOW)

    await maintenance_service.cancel_maintenance_record(
        str(cancelled_id), {"reason": "Incorrect repair scope"}, _actor()
    )
    cancel_retry = await maintenance_service.cancel_maintenance_record(
        str(cancelled_id), {"reason": "Incorrect repair scope"}, _actor()
    )
    replacement = await inspection_service.decide_inspection(str(inspection["_id"]), {
        "decision": "maintenance_required",
        "notes": "Revised brake work",
        "maintenance_system": "braking",
        "issue_type": "Brake caliper repair",
        "priority": "high",
        "estimated_cost": 55_000,
    }, _actor())

    assert len(db[MAINTENANCE_COLLECTION].rows) == 2
    assert db[MAINTENANCE_COLLECTION].rows[0]["work_order_status"] == "cancelled"
    assert cancel_retry["id"] == str(cancelled_id)
    assert replacement["work_order"]["id"] != str(cancelled_id)
    assert replacement["inspection"]["work_order_id"] == replacement["work_order"]["id"]


@pytest.mark.asyncio
async def test_completion_requires_evidence_reassesses_closes_inspection_and_releases_when_ready(monkeypatch) -> None:
    db, inspection = _base_records(review_status=None)
    order_id = ObjectId()
    db[INSPECTION_COLLECTION].rows[0].update({"status": "maintenance_required", "work_order_id": order_id})
    db[VEHICLE_COLLECTION].rows[0]["status"] = "under_maintenance"
    db[MAINTENANCE_COLLECTION].rows.append({
        "_id": order_id,
        "vehicle_id": inspection["vehicle_id"],
        "inspection_id": inspection["_id"],
        "assessment_id": inspection["assessment_id"],
        "part_name": "Braking",
        "maintenance_system": "braking",
        "issue_type": "Brake wear",
        "service_date": NOW,
        "mileage_at_service": 48_200,
        "priority": "high",
        "status": "in_progress",
        "work_order_status": "in_progress",
        "created_by": ObjectId(),
        "created_at": NOW,
        "updated_at": NOW,
    })
    monkeypatch.setattr(maintenance_service, "_db", lambda: db)
    monkeypatch.setattr(maintenance_service, "get_maintenance_collection", lambda: db[MAINTENANCE_COLLECTION])
    monkeypatch.setattr(maintenance_service, "utc_now", lambda: NOW)
    monkeypatch.setattr(maintenance_service, "reset_part_after_maintenance", lambda *args: _noop())
    monkeypatch.setattr(maintenance_service, "create_maintenance_alert", lambda *args, **kwargs: _noop())
    from app.services import predictive_maintenance_service
    monkeypatch.setattr(predictive_maintenance_service, "_db", lambda: db)

    async def recalculate(*args, **kwargs):
        db[PREDICTION_COLLECTION].rows[0].update({
            "risk_level": "low", "dispatch_hold": False, "review_status": "not_required"
        })
        return {"risk_level": "low", "dispatch_hold": False, "review_status": "not_required"}

    monkeypatch.setattr(maintenance_service, "_recalculate_after_completion", recalculate)
    completed = await maintenance_service.complete_maintenance_record(str(order_id), {
        "actual_cost": 40_000,
        "completion_evidence": "Brake pads replaced and road test passed",
        "notes": "Completed",
    }, _actor())
    completed_retry = await maintenance_service.complete_maintenance_record(str(order_id), {
        "actual_cost": 40_000,
        "completion_evidence": "Brake pads replaced and road test passed",
        "notes": "Completed",
    }, _actor())

    assert completed["work_order_status"] == "completed"
    assert completed["actual_cost"] == 40_000
    assert completed["completion_evidence"] == "Brake pads replaced and road test passed"
    assert completed_retry["id"] == completed["id"]
    assert db[INSPECTION_COLLECTION].rows[0]["is_active"] is False
    assert db[INSPECTION_COLLECTION].rows[0]["status"] == "maintenance_completed"
    assert db[VEHICLE_COLLECTION].rows[0]["status"] == "active"


def test_public_inspection_normalizes_legacy_completed_maintenance_status() -> None:
    inspection = {
        "_id": ObjectId(),
        "status": "maintenance_required",
        "is_active": False,
        "maintenance_completed_at": NOW,
    }

    public = inspection_service._public(inspection)

    assert public is not None
    assert public["status"] == "maintenance_completed"


async def _noop(*args, **kwargs):
    return None
