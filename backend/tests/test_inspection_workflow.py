from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException, Request
from pydantic import ValidationError
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.models.inspection_model import INSPECTION_COLLECTION
from app.models.predictive_model import PREDICTION_COLLECTION
from app.models.user_model import USER_COLLECTION
from app.schemas.inspection_schema import InspectionDraftRequest, InspectionResponse
from app.services import inspection_service
from app.services.fleet_intelligence_service import classify_vehicle_readiness


NOW = datetime(2026, 8, 27, 10, 0, tzinfo=timezone.utc)


def _matches(document: dict, query: dict) -> bool:
    for key, expected in query.items():
        actual = document.get(key)
        if isinstance(expected, dict):
            if "$in" in expected and actual not in expected["$in"]:
                return False
            if "$ne" in expected and actual == expected["$ne"]:
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

    async def to_list(self, length: int | None):
        return deepcopy(self.rows if length is None else self.rows[:length])


class _Collection:
    def __init__(self, rows: list[dict] | None = None):
        self.rows = deepcopy(rows or [])
        self.atomic_calls: list[tuple[dict, dict, object]] = []
        self.raise_duplicate = False

    async def find_one(self, query: dict, **kwargs):
        return next((deepcopy(row) for row in self.rows if _matches(row, query)), None)

    def find(self, query: dict, projection: dict | None = None):
        rows = [deepcopy(row) for row in self.rows if _matches(row, query)]
        if projection:
            included = {key for key, enabled in projection.items() if enabled}
            rows = [
                {key: value for key, value in row.items() if key in included or key == "_id"}
                for row in rows
            ]
        return _Cursor(rows)

    async def count_documents(self, query: dict):
        return sum(1 for row in self.rows if _matches(row, query))

    async def insert_one(self, document: dict):
        if self.raise_duplicate:
            raise DuplicateKeyError("active inspection exists")
        row = deepcopy(document)
        row["_id"] = ObjectId()
        self.rows.append(row)
        return SimpleNamespace(inserted_id=row["_id"])

    async def find_one_and_update(self, query: dict, update: dict, return_document=None):
        self.atomic_calls.append((deepcopy(query), deepcopy(update), return_document))
        for index, row in enumerate(self.rows):
            if _matches(row, query):
                before = deepcopy(row)
                row.update(deepcopy(update.get("$set", {})))
                self.rows[index] = row
                return deepcopy(row if return_document == ReturnDocument.AFTER else before)
        return None


def _database(*, prediction: dict | None = None, inspections: list[dict] | None = None,
              users: list[dict] | None = None):
    return {
        PREDICTION_COLLECTION: _Collection([prediction] if prediction else []),
        INSPECTION_COLLECTION: _Collection(inspections),
        USER_COLLECTION: _Collection(users),
    }


def _actor(role: str = "maintenance_manager") -> dict:
    return {"id": str(ObjectId()), "role": role, "permissions": ["maintenance.manage", "maintenance.view"]}


@pytest.mark.asyncio
async def test_create_requires_assessment_vehicle_and_feature_hash_and_deduplicates(monkeypatch) -> None:
    vehicle_id, assessment_id = ObjectId(), ObjectId()
    prediction = {
        "_id": assessment_id,
        "vehicle_id": vehicle_id,
        "feature_hash": "same-feature-hash",
        "risk_level": "high",
        "system_risks": [{"system": "braking"}],
    }
    db = _database(prediction=prediction)
    monkeypatch.setattr(inspection_service, "_db", lambda: db)
    monkeypatch.setattr(inspection_service, "utc_now", lambda: NOW)
    payload = {
        "vehicle_id": str(vehicle_id),
        "assessment_id": str(assessment_id),
        "feature_hash": "same-feature-hash",
        "priority": "high",
        "inspection_areas": ["braking"],
    }

    created = await inspection_service.create_inspection(payload, _actor())
    duplicate = await inspection_service.create_inspection(payload, _actor())

    assert created["id"] == duplicate["id"]
    assert len(db[INSPECTION_COLLECTION].rows) == 1
    assert created["status"] == "pending"
    assert created["is_active"] is True

    with pytest.raises(HTTPException, match="feature hash") as mismatch:
        await inspection_service.create_inspection({**payload, "feature_hash": "different-hash"}, _actor())
    assert mismatch.value.status_code == 409

    with pytest.raises(HTTPException, match="same vehicle") as wrong_vehicle:
        await inspection_service.create_inspection({**payload, "vehicle_id": str(ObjectId())}, _actor())
    assert wrong_vehicle.value.status_code == 409


@pytest.mark.asyncio
async def test_create_recovers_from_unique_index_race(monkeypatch) -> None:
    vehicle_id, assessment_id = ObjectId(), ObjectId()
    prediction = {"_id": assessment_id, "vehicle_id": vehicle_id, "feature_hash": "hash-race"}
    existing = {
        "_id": ObjectId(), "vehicle_id": vehicle_id, "assessment_id": assessment_id,
        "feature_hash": "hash-race", "status": "pending", "is_active": True,
        "priority": "high", "inspection_areas": [], "created_by": ObjectId(),
        "created_at": NOW, "updated_at": NOW,
    }
    db = _database(prediction=prediction, inspections=[existing])
    db[INSPECTION_COLLECTION].raise_duplicate = True
    monkeypatch.setattr(inspection_service, "_db", lambda: db)

    result = await inspection_service.create_inspection({
        "vehicle_id": str(vehicle_id), "assessment_id": str(assessment_id),
        "feature_hash": "hash-race", "priority": "high", "inspection_areas": [],
    }, _actor())

    assert result["id"] == str(existing["_id"])


@pytest.mark.asyncio
async def test_assignment_requires_active_engineering_user_and_atomic_pending_transition(monkeypatch) -> None:
    inspection_id, vehicle_id, assessment_id, assignee_id = ObjectId(), ObjectId(), ObjectId(), ObjectId()
    inspection = {
        "_id": inspection_id, "vehicle_id": vehicle_id, "assessment_id": assessment_id,
        "feature_hash": "hash", "status": "pending", "is_active": True,
        "priority": "high", "inspection_areas": [], "created_by": ObjectId(),
        "created_at": NOW, "updated_at": NOW,
    }
    active_manager = {"_id": assignee_id, "role": "maintenance_manager", "is_active": True}
    db = _database(inspections=[inspection], users=[active_manager])
    monkeypatch.setattr(inspection_service, "_db", lambda: db)
    monkeypatch.setattr(inspection_service, "utc_now", lambda: NOW)
    actor = _actor("admin")

    assigned = await inspection_service.assign_inspection(
        str(inspection_id), {"assigned_to": str(assignee_id)}, actor
    )

    assert assigned["status"] == "assigned"
    query, _, mode = db[INSPECTION_COLLECTION].atomic_calls[-1]
    assert query == {"_id": inspection_id, "status": "pending", "is_active": True}
    assert mode == ReturnDocument.AFTER

    invalid_db = _database(inspections=[inspection], users=[{
        "_id": assignee_id, "role": "fleet_manager", "is_active": True,
    }])
    monkeypatch.setattr(inspection_service, "_db", lambda: invalid_db)
    with pytest.raises(HTTPException, match="active administrator or maintenance manager") as exc:
        await inspection_service.assign_inspection(str(inspection_id), {"assigned_to": str(assignee_id)}, actor)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_start_and_complete_are_atomic_and_completion_retains_elapsed_evidence(monkeypatch) -> None:
    inspection_id, assignee_id = ObjectId(), ObjectId()
    started_at = NOW - timedelta(minutes=42, seconds=7)
    inspection = {
        "_id": inspection_id, "vehicle_id": ObjectId(), "assessment_id": ObjectId(),
        "feature_hash": "hash", "status": "assigned", "is_active": True,
        "priority": "high", "inspection_areas": [], "assigned_to": assignee_id,
        "created_by": ObjectId(), "created_at": NOW - timedelta(days=1), "updated_at": NOW,
    }
    db = _database(inspections=[inspection])
    monkeypatch.setattr(inspection_service, "_db", lambda: db)
    actor = {"id": str(assignee_id), "role": "maintenance_manager"}
    monkeypatch.setattr(inspection_service, "utc_now", lambda: started_at)
    started = await inspection_service.start_inspection(str(inspection_id), {}, actor)
    assert started["status"] == "in_progress"

    monkeypatch.setattr(inspection_service, "utc_now", lambda: NOW)
    completed = await inspection_service.complete_inspection(str(inspection_id), {
        "checklist": [{"key": "brakes", "label": "Brake condition", "outcome": "passed", "remark": None}],
        "summary": "Inspection complete",
    }, actor)

    assert completed["status"] == "decision_pending"
    assert completed["completed_at"] == NOW
    assert completed["elapsed_seconds"] == 2527
    assert completed["is_active"] is True
    query, update, _ = db[INSPECTION_COLLECTION].atomic_calls[-1]
    assert query["status"] == "in_progress"
    assert update["$set"]["completed_at"] == NOW
    assert update["$set"]["decision_pending_at"] == NOW


@pytest.mark.asyncio
async def test_draft_save_is_atomic_and_restored_by_public_response(monkeypatch) -> None:
    inspection_id, assignee_id = ObjectId(), ObjectId()
    inspection = {
        "_id": inspection_id, "vehicle_id": ObjectId(), "assessment_id": ObjectId(),
        "feature_hash": "hash", "status": "in_progress", "is_active": True,
        "priority": "high", "inspection_areas": ["braking"], "assigned_to": assignee_id,
        "checklist": [], "summary": None, "created_by": ObjectId(),
        "created_at": NOW, "updated_at": NOW,
    }
    db = _database(inspections=[inspection])
    monkeypatch.setattr(inspection_service, "_db", lambda: db)
    monkeypatch.setattr(inspection_service, "utc_now", lambda: NOW)
    actor = {"id": str(assignee_id), "role": "maintenance_manager"}
    checklist = [{
        "key": "brakes", "label": "Brake condition", "outcome": "failed",
        "remark": "Rear pads below service limit",
    }]

    saved = await inspection_service.save_inspection_draft(
        str(inspection_id), {"checklist": checklist, "summary": "Partial inspection"}, actor
    )
    restored = await inspection_service.get_inspection(str(inspection_id))

    assert saved["draft_checklist"] == checklist
    assert restored["draft_summary"] == "Partial inspection"
    assert restored["draft_saved_by"] == str(assignee_id)
    assert restored["draft_saved_at"] == NOW
    assert restored["checklist"] == []
    assert restored["summary"] is None
    query, update, mode = db[INSPECTION_COLLECTION].atomic_calls[-1]
    assert query == {
        "_id": inspection_id, "status": "in_progress", "is_active": True,
        "assigned_to": assignee_id,
    }
    assert update["$set"]["draft_checklist"] == checklist
    assert mode == ReturnDocument.AFTER

    response = InspectionResponse.model_validate(restored)
    assert response.draft_summary == "Partial inspection"


@pytest.mark.asyncio
async def test_partial_draft_update_preserves_omitted_checklist(monkeypatch) -> None:
    inspection_id, assignee_id = ObjectId(), ObjectId()
    existing_checklist = [{
        "key": "tires", "label": "Tire condition", "outcome": "passed", "remark": None,
    }]
    db = _database(inspections=[{
        "_id": inspection_id, "vehicle_id": ObjectId(), "assessment_id": ObjectId(),
        "feature_hash": "hash", "status": "in_progress", "is_active": True,
        "priority": "medium", "inspection_areas": [], "assigned_to": assignee_id,
        "draft_checklist": existing_checklist, "draft_summary": "Earlier note",
        "created_by": ObjectId(), "created_at": NOW, "updated_at": NOW,
    }])
    monkeypatch.setattr(inspection_service, "_db", lambda: db)
    monkeypatch.setattr(inspection_service, "utc_now", lambda: NOW)

    saved = await inspection_service.save_inspection_draft(
        str(inspection_id), {"summary": None},
        {"id": str(assignee_id), "role": "maintenance_manager"},
    )

    assert saved["draft_checklist"] == existing_checklist
    assert saved["draft_summary"] is None
    update = db[INSPECTION_COLLECTION].atomic_calls[-1][1]["$set"]
    assert "draft_checklist" not in update


@pytest.mark.asyncio
async def test_draft_save_rejects_inactive_or_non_in_progress_inspection(monkeypatch) -> None:
    inspection_id, assignee_id = ObjectId(), ObjectId()
    actor = {"id": str(assignee_id), "role": "maintenance_manager"}
    for status_value, is_active in [("assigned", True), ("in_progress", False)]:
        db = _database(inspections=[{
            "_id": inspection_id, "vehicle_id": ObjectId(), "assessment_id": ObjectId(),
            "feature_hash": "hash", "status": status_value, "is_active": is_active,
            "priority": "high", "inspection_areas": [], "assigned_to": assignee_id,
            "created_by": ObjectId(), "created_at": NOW, "updated_at": NOW,
        }])
        monkeypatch.setattr(inspection_service, "_db", lambda db=db: db)

        with pytest.raises(HTTPException) as exc:
            await inspection_service.save_inspection_draft(
                str(inspection_id), {"summary": "Work in progress"}, actor
            )
        assert exc.value.status_code == 409


def test_draft_schema_accepts_partial_blank_summary_and_validates_failed_remarks() -> None:
    assert InspectionDraftRequest().model_dump(exclude_unset=True) == {}
    assert InspectionDraftRequest(checklist=[]).checklist == []
    assert InspectionDraftRequest(summary=" ").summary is None
    assert InspectionDraftRequest(summary=None).summary is None

    with pytest.raises(ValidationError, match="remark is required"):
        InspectionDraftRequest(checklist=[{
            "key": "brakes", "label": "Brake condition", "outcome": "failed", "remark": " ",
        }])


@pytest.mark.asyncio
async def test_completion_atomically_clears_saved_draft(monkeypatch) -> None:
    inspection_id, assignee_id = ObjectId(), ObjectId()
    inspection = {
        "_id": inspection_id, "vehicle_id": ObjectId(), "assessment_id": ObjectId(),
        "feature_hash": "hash", "status": "in_progress", "is_active": True,
        "priority": "high", "inspection_areas": [], "assigned_to": assignee_id,
        "started_at": NOW - timedelta(minutes=10),
        "draft_checklist": [{
            "key": "brakes", "label": "Brake condition", "outcome": "passed", "remark": None,
        }],
        "draft_summary": "Draft", "draft_saved_by": assignee_id,
        "draft_saved_at": NOW - timedelta(minutes=2),
        "created_by": ObjectId(), "created_at": NOW, "updated_at": NOW,
    }
    db = _database(inspections=[inspection])
    monkeypatch.setattr(inspection_service, "_db", lambda: db)
    monkeypatch.setattr(inspection_service, "utc_now", lambda: NOW)

    completed = await inspection_service.complete_inspection(str(inspection_id), {
        "checklist": [{
            "key": "brakes", "label": "Brake condition", "outcome": "passed", "remark": None,
        }],
        "summary": "Final inspection evidence",
    }, {"id": str(assignee_id), "role": "maintenance_manager"})

    assert completed["status"] == "decision_pending"
    assert completed["summary"] == "Final inspection evidence"
    assert completed["draft_checklist"] == []
    assert completed["draft_summary"] is None
    assert completed["draft_saved_by"] is None
    assert completed["draft_saved_at"] is None
    final_update = db[INSPECTION_COLLECTION].atomic_calls[-1][1]["$set"]
    assert final_update["checklist"] == completed["checklist"]
    assert final_update["draft_checklist"] == []


@pytest.mark.asyncio
async def test_cancel_requires_reason_and_deactivates_with_atomic_state_filter(monkeypatch) -> None:
    inspection_id = ObjectId()
    inspection = {
        "_id": inspection_id, "vehicle_id": ObjectId(), "assessment_id": ObjectId(),
        "feature_hash": "hash", "status": "in_progress", "is_active": True,
        "priority": "high", "inspection_areas": [], "started_at": NOW - timedelta(minutes=5),
        "created_by": ObjectId(), "created_at": NOW, "updated_at": NOW,
    }
    db = _database(inspections=[inspection])
    monkeypatch.setattr(inspection_service, "_db", lambda: db)
    monkeypatch.setattr(inspection_service, "utc_now", lambda: NOW)

    cancelled = await inspection_service.cancel_inspection(
        str(inspection_id), {"reason": "Vehicle was removed from service"}, _actor("admin")
    )

    assert cancelled["status"] == "cancelled"
    assert cancelled["is_active"] is False
    assert cancelled["elapsed_seconds"] == 300
    assert db[INSPECTION_COLLECTION].atomic_calls[-1][0]["status"] == {"$in": ["pending", "assigned", "in_progress"]}


def test_active_inspection_blocks_authoritative_readiness() -> None:
    result = classify_vehicle_readiness(
        {"status": "active", "health_status": "healthy"},
        {"risk_level": "low"},
        None,
        {"status": "decision_pending", "is_active": True},
    )
    assert result["eligible"] is False
    assert "Active vehicle inspection is awaiting a service decision" in result["blocking_reasons"]


@pytest.mark.asyncio
async def test_inspection_routes_enforce_view_and_manage_roles() -> None:
    from app.routes.inspection_routes import router

    list_route = next(route for route in router.routes if route.path == "/inspections" and "GET" in route.methods)
    create_route = next(route for route in router.routes if route.path == "/inspections" and "POST" in route.methods)
    list_dependency = list_route.dependant.dependencies[0].call
    create_dependency = create_route.dependant.dependencies[0].call
    request = Request({
        "type": "http", "method": "GET", "path": "/api/inspections",
        "headers": [], "query_string": b"", "server": ("test", 80), "client": ("test", 1),
    })

    with pytest.raises(HTTPException) as view_denied:
        await list_dependency(request, {"role": "route_planner", "permissions": []})
    assert view_denied.value.status_code == 403

    request.scope["method"] = "POST"
    with pytest.raises(HTTPException) as manage_denied:
        await create_dependency(request, {"role": "fleet_manager", "permissions": []})
    assert manage_denied.value.status_code == 403


@pytest.mark.asyncio
async def test_inspection_draft_route_uses_manage_permission_and_forwards_partial_payload(monkeypatch) -> None:
    from app.routes import inspection_routes

    route = next(
        route for route in inspection_routes.router.routes
        if route.path == "/inspections/{inspection_id}/draft" and "PATCH" in route.methods
    )
    dependency = route.dependant.dependencies[0].call
    request = Request({
        "type": "http", "method": "PATCH", "path": "/api/inspections/example/draft",
        "headers": [], "query_string": b"", "server": ("test", 80), "client": ("test", 1),
    })
    with pytest.raises(HTTPException) as denied:
        await dependency(request, {"role": "fleet_manager", "permissions": []})
    assert denied.value.status_code == 403
    assert await dependency(request, {"role": "maintenance_manager", "permissions": ["maintenance.manage"]})

    captured: dict = {}

    async def _save(inspection_id: str, payload: dict, actor: dict):
        captured.update({"inspection_id": inspection_id, "payload": payload, "actor": actor})
        return {"id": inspection_id, "draft_summary": None}

    monkeypatch.setattr(inspection_routes, "save_inspection_draft", _save)
    actor = {"id": str(ObjectId()), "role": "maintenance_manager"}
    response = await inspection_routes.inspection_draft(
        "inspection-id", InspectionDraftRequest(summary=None), actor
    )

    assert captured["payload"] == {"summary": None}
    assert response["data"]["draft_summary"] is None


@pytest.mark.asyncio
async def test_list_inspection_assignees_returns_only_minimal_active_eligible_users(monkeypatch) -> None:
    admin_id, manager_id = ObjectId(), ObjectId()
    db = _database(users=[
        {
            "_id": manager_id,
            "full_name": "Zara Mechanic",
            "email": "zara@example.com",
            "password_hash": "secret",
            "permission_overrides": {"allow": ["users.manage"]},
            "role": "maintenance_manager",
            "is_active": True,
        },
        {
            "_id": admin_id,
            "full_name": "Amal Admin",
            "email": "amal@example.com",
            "password_hash": "secret",
            "role": "admin",
            "is_active": True,
        },
        {
            "_id": ObjectId(), "full_name": "Inactive Admin", "role": "admin", "is_active": False,
        },
        {
            "_id": ObjectId(), "full_name": "Fleet Viewer", "role": "fleet_manager", "is_active": True,
        },
    ])
    monkeypatch.setattr(inspection_service, "_db", lambda: db)

    result = await inspection_service.list_inspection_assignees()

    assert result == [
        {"id": str(admin_id), "full_name": "Amal Admin", "role": "admin"},
        {"id": str(manager_id), "full_name": "Zara Mechanic", "role": "maintenance_manager"},
    ]
    assert all(set(item) == {"id", "full_name", "role"} for item in result)


@pytest.mark.asyncio
async def test_inspection_assignee_route_uses_view_permission_and_precedes_dynamic_detail() -> None:
    from app.routes import inspection_routes

    router = inspection_routes.router

    assignee_route_index = next(
        index for index, route in enumerate(router.routes)
        if route.path == "/inspections/assignees" and "GET" in route.methods
    )
    detail_route_index = next(
        index for index, route in enumerate(router.routes)
        if route.path == "/inspections/{inspection_id}" and "GET" in route.methods
    )
    route = router.routes[assignee_route_index]
    dependency = route.dependant.dependencies[0].call
    request = Request({
        "type": "http", "method": "GET", "path": "/api/inspections/assignees",
        "headers": [], "query_string": b"", "server": ("test", 80), "client": ("test", 1),
    })

    assert assignee_route_index < detail_route_index
    with pytest.raises(HTTPException) as denied:
        await dependency(request, {"role": "route_planner", "permissions": []})
    assert denied.value.status_code == 403
    assert await dependency(request, {"role": "fleet_manager", "permissions": ["maintenance.view"]})


@pytest.mark.asyncio
async def test_inspection_assignee_route_returns_minimal_items_envelope(monkeypatch) -> None:
    from app.routes import inspection_routes

    assignee = {
        "id": str(ObjectId()),
        "full_name": "Nimali Perera",
        "role": "maintenance_manager",
    }

    async def _assignees():
        return [assignee]

    monkeypatch.setattr(inspection_routes, "list_inspection_assignees", _assignees)

    response = await inspection_routes.inspection_assignees({"role": "fleet_manager"})

    assert response == {
        "success": True,
        "message": "Inspection assignees retrieved",
        "data": {"items": [assignee]},
    }
