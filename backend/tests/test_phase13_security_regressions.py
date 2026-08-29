from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.models.maintenance_intelligence_model import PREDICTION_REVIEW_COLLECTION
from app.models.predictive_model import PREDICTION_COLLECTION
from app.services import (
    driver_device_service,
    maintenance_service,
    predictive_maintenance_service,
    route_optimizer_service,
)


class _Collection:
    def __init__(self, result=None, *, duplicate_on_update=False):
        self.result = result
        self.duplicate_on_update = duplicate_on_update
        self.updates = []
        self.deletes = []

    async def find_one(self, query, **kwargs):
        return self.result

    async def update_one(self, query, update):
        self.updates.append((query, update))
        if self.duplicate_on_update:
            raise DuplicateKeyError("active assignment conflict")
        return SimpleNamespace(matched_count=1)

    async def update_many(self, query, update):
        self.updates.append((query, update))
        return SimpleNamespace(matched_count=1)

    async def delete_one(self, query):
        self.deletes.append(query)
        return SimpleNamespace(deleted_count=1)


@pytest.mark.asyncio
async def test_confirmed_review_cannot_be_cleared_directly(monkeypatch) -> None:
    review_id = ObjectId()
    review = {
        "_id": review_id,
        "vehicle_id": ObjectId(),
        "feature_hash": "hash-1",
        "status": "confirmed",
        "linked_maintenance_record_id": ObjectId(),
    }
    reviews = _Collection(review)
    monkeypatch.setattr(
        predictive_maintenance_service,
        "_db",
        lambda: {PREDICTION_REVIEW_COLLECTION: reviews},
    )

    with pytest.raises(HTTPException) as exc:
        await predictive_maintenance_service.resolve_prediction_review(
            str(review_id),
            {"resolution": "cleared", "notes": "Attempted early clearance"},
            {"id": str(ObjectId())},
        )

    assert exc.value.status_code == 409
    assert "maintenance" in str(exc.value.detail).lower()
    assert reviews.updates == []


@pytest.mark.asyncio
async def test_existing_critical_prediction_repairs_missing_review(monkeypatch) -> None:
    vehicle_id, prediction_id, review_id = ObjectId(), ObjectId(), ObjectId()
    vehicle = {"_id": vehicle_id, "registration_number": "WP TEST-1000"}
    prediction = {
        "_id": prediction_id,
        "vehicle_id": vehicle_id,
        "feature_hash": "feature-hash",
        "model_version": "fleetopt-sensor-free-pm-v1",
        "risk_level": "critical",
        "dispatch_hold": True,
        "failure_probability": 0.9,
        "input_source": "manual_recalculation",
        "failure_prediction": 1,
        "recommended_action": "Review vehicle",
    }
    created = []
    predictions = _Collection()

    async def create_review(*args):
        created.append(args)
        return {
            "_id": review_id,
            "vehicle_id": vehicle_id,
            "prediction_id": prediction_id,
            "feature_hash": "feature-hash",
            "status": "pending",
        }

    monkeypatch.setattr(predictive_maintenance_service, "_get_vehicle", lambda *_: _async(vehicle))
    monkeypatch.setattr(
        predictive_maintenance_service.predictive_artifact_registry,
        "get",
        lambda: SimpleNamespace(model_version="fleetopt-sensor-free-pm-v1"),
    )
    monkeypatch.setattr(
        predictive_maintenance_service,
        "build_vehicle_features",
        lambda *_: _async(SimpleNamespace(feature_hash="feature-hash")),
    )
    monkeypatch.setattr(
        predictive_maintenance_service,
        "get_assessment_eligibility",
        lambda *_: _async({"eligible": True, "blocking_reasons": []}),
    )
    monkeypatch.setattr(
        predictive_maintenance_service,
        "_find_existing_prediction",
        lambda *_: _async(prediction),
    )
    monkeypatch.setattr(
        predictive_maintenance_service,
        "_find_review_for_hash",
        lambda *_: _async(None),
    )
    monkeypatch.setattr(predictive_maintenance_service, "_create_review", create_review)
    monkeypatch.setattr(
        predictive_maintenance_service,
        "_cache_vehicle_assessment_risk",
        lambda *_: _async(None),
    )
    monkeypatch.setattr(
        predictive_maintenance_service,
        "_db",
        lambda: {PREDICTION_COLLECTION: predictions},
    )

    result = await predictive_maintenance_service.recalculate_vehicle_maintenance(
        str(vehicle_id), {"trigger": "manual_recalculation"}, {"id": str(ObjectId())}
    )

    assert len(created) == 1
    assert result["review_status"] == "pending"
    assert result["dispatch_hold"] is True


@pytest.mark.asyncio
async def test_linked_review_cannot_be_used_for_second_maintenance(monkeypatch) -> None:
    vehicle_id, review_id = ObjectId(), ObjectId()
    db = {
        "vehicles": _Collection({"_id": vehicle_id}),
        PREDICTION_REVIEW_COLLECTION: _Collection({
            "_id": review_id,
            "vehicle_id": vehicle_id,
            "status": "confirmed",
            "linked_maintenance_record_id": ObjectId(),
        }),
    }
    monkeypatch.setattr(maintenance_service, "_db", lambda: db)

    with pytest.raises(HTTPException) as exc:
        await maintenance_service._prepare_record_data({
            "vehicle_id": str(vehicle_id),
            "prediction_review_id": str(review_id),
            "part_id": None,
        })

    assert exc.value.status_code == 409
    assert "already linked" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_duplicate_active_assignment_returns_conflict(monkeypatch) -> None:
    route_id, vehicle_id, driver_id = ObjectId(), ObjectId(), ObjectId()
    route = {
        "_id": route_id,
        "route_code": "ROUTE-RACE",
        "status": "optimized",
        "vehicle_id": vehicle_id,
        "driver_id": driver_id,
        "delivery_order_ids": [],
    }
    routes = _Collection(route, duplicate_on_update=True)
    monkeypatch.setattr(route_optimizer_service, "get_route_plan_collection", lambda: routes)
    monkeypatch.setattr(
        route_optimizer_service,
        "validate_vehicle_assignment",
        lambda *_args, **_kwargs: _async({
            "eligible": True,
            "vehicle_registration": "WP TEST-1000",
            "blocking_reasons": [],
        }),
    )
    monkeypatch.setattr(
        driver_device_service,
        "validate_driver_for_assignment",
        lambda *_args, **_kwargs: _async({}),
    )

    with pytest.raises(HTTPException) as exc:
        await route_optimizer_service.dispatch_route(str(route_id), {}, {"id": str(ObjectId())})

    assert exc.value.status_code == 409
    assert "already assigned" in str(exc.value.detail).lower()
    assert routes.updates[0][0]["status"] == {"$nin": ["dispatched", "in_progress", "completed", "cancelled"]}


async def _async(value):
    return value
