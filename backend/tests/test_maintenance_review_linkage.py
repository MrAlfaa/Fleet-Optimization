from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.models.maintenance_intelligence_model import PREDICTION_REVIEW_COLLECTION
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.schemas.maintenance_schema import MaintenanceRecordCreate
from app.services import maintenance_service, predictive_maintenance_service


class _FindCollection:
    def __init__(self, result=None):
        self.result = result
        self.last_query = None

    async def find_one(self, query, **kwargs):
        self.last_query = query
        return self.result

    def find(self, query):
        self.last_query = query
        return self

    async def to_list(self, length):
        return self.result or []


def test_maintenance_create_accepts_review_id_alias() -> None:
    payload = MaintenanceRecordCreate(
        vehicle_id=str(ObjectId()), part_name="Brake Pads", maintenance_type="corrective",
        maintenance_system="braking", event_kind="corrective_repair", issue_type="Confirmed wear",
        service_date="2026-08-24T00:00:00Z", mileage_at_service=42000,
        prediction_review_id=None, review_id=str(ObjectId()),
    )
    assert payload.prediction_review_id == payload.review_id


@pytest.mark.asyncio
async def test_review_vehicle_must_match_maintenance_vehicle(monkeypatch) -> None:
    vehicle_id, other_vehicle_id, review_id = ObjectId(), ObjectId(), ObjectId()
    db = {
        VEHICLE_COLLECTION: _FindCollection({"_id": vehicle_id}),
        PREDICTION_REVIEW_COLLECTION: _FindCollection({"_id": review_id, "vehicle_id": other_vehicle_id, "status": "confirmed"}),
    }
    monkeypatch.setattr(maintenance_service, "_db", lambda: db)
    with pytest.raises(HTTPException, match="another vehicle"):
        await maintenance_service._prepare_record_data({
            "vehicle_id": str(vehicle_id), "prediction_review_id": str(review_id), "part_id": None,
        })


@pytest.mark.asyncio
async def test_completion_selects_only_reviews_linked_to_exact_record(monkeypatch) -> None:
    vehicle_id, record_id = ObjectId(), ObjectId()
    reviews = _FindCollection([])
    monkeypatch.setattr(predictive_maintenance_service, "_db", lambda: {PREDICTION_REVIEW_COLLECTION: reviews})
    await predictive_maintenance_service.clear_reviews_for_completed_maintenance(
        {"_id": record_id, "vehicle_id": vehicle_id}, {"id": str(ObjectId())}
    )
    assert reviews.last_query == {
        "vehicle_id": vehicle_id,
        "status": "confirmed",
        "linked_maintenance_record_id": record_id,
    }
