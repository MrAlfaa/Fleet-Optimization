from types import SimpleNamespace

import pytest
from bson import ObjectId

from app.models.vehicle_model import VEHICLE_COLLECTION
from app.services import driver_service


class _VehicleCollection:
    def __init__(self, vehicle):
        self.vehicle = vehicle

    async def find_one(self, query):
        return self.vehicle


@pytest.mark.asyncio
async def test_assigned_vehicle_exposes_powertrain_fields_and_operational_model_status(monkeypatch) -> None:
    vehicle_id = ObjectId()
    vehicle = {
        "_id": vehicle_id, "vehicle_code": "FLT-1", "registration_number": "WP CAA-1000",
        "vehicle_type": "diesel_van", "vehicle_category": "van", "fuel_type": "diesel",
        "payload_capacity_kg": 1400, "brand": "Test", "model": "Cargo", "status": "active",
        "health_status": "healthy", "current_mileage": 42000,
    }
    monkeypatch.setattr(driver_service, "get_assigned_route_raw", lambda *_: _async_value({"vehicle_id": vehicle_id}))
    monkeypatch.setattr(driver_service, "_db", lambda: {VEHICLE_COLLECTION: _VehicleCollection(vehicle)})
    monkeypatch.setattr(driver_service.predictive_artifact_registry, "status", lambda: {"available": True})

    result = await driver_service.get_assigned_vehicle({"id": str(ObjectId())})

    assert result["fuel_type"] == "diesel"
    assert result["vehicle_category"] == "van"
    assert result["payload_capacity_kg"] == 1400
    assert result["model_status"] == "available"
    assert "backend" not in result["model_status"].lower()


async def _async_value(value):
    return value
