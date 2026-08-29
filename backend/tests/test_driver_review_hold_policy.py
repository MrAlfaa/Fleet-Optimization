from types import SimpleNamespace

import pytest
from bson import ObjectId

from app.models.driver_execution_model import VEHICLE_TRIP_INSPECTION_COLLECTION
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.services import driver_inspection_service as service


class _Collection:
    def __init__(self):
        self.updates = []
        self.find_result = None

    async def find_one(self, query, **kwargs):
        return self.find_result

    async def insert_one(self, document):
        return SimpleNamespace(inserted_id=ObjectId())

    async def update_one(self, query, update):
        self.updates.append((query, update))
        return SimpleNamespace(matched_count=1)


@pytest.mark.asyncio
async def test_model_only_review_hold_does_not_set_vehicle_under_maintenance(monkeypatch) -> None:
    route_id, vehicle_id, driver_id, prediction_id = ObjectId(), ObjectId(), ObjectId(), ObjectId()
    route = {"_id": route_id, "route_code": "R-1", "vehicle_id": vehicle_id}
    vehicle = {"_id": vehicle_id, "current_mileage": 42000, "registration_number": "WP TEST"}
    inspections, vehicles = _Collection(), _Collection()
    monkeypatch.setattr(service, "_db", lambda: {
        VEHICLE_TRIP_INSPECTION_COLLECTION: inspections,
        VEHICLE_COLLECTION: vehicles,
    })
    monkeypatch.setattr(service, "_assigned_route", lambda *_: _async_value(route))
    monkeypatch.setattr(service, "_vehicle", lambda *_: _async_value(vehicle))
    monkeypatch.setattr(service, "_run_limited_prediction", lambda *_: _async_value(({
        "id": str(prediction_id), "risk_level": "critical", "dispatch_hold": True,
    }, None)))
    monkeypatch.setattr(service, "_create_block_alert", lambda *_: _async_value(None))

    result = await service.submit_pre_trip_inspection({
        "odometer": 42000, "battery_soc": None, "tire_condition": "normal",
        "brake_condition": "normal", "powertrain_condition": "normal",
        "charging_or_fuel_issue": "none", "vehicle_damage": "none",
        "dashboard_warning": "none", "unusual_noise": "none", "vibration_level": "none",
    }, {"id": str(driver_id)})

    assert result["safe_to_operate"] is True
    assert result["observation_safe_to_operate"] is True
    assert result["review_hold"] is True
    assert result["blocking_reasons"] == []
    assert all(update[1]["$set"].get("status") != "under_maintenance" for update in vehicles.updates)

    inspections.find_result = {
        **result,
        "_id": ObjectId(result["id"]),
        "route_id": route_id,
        "driver_id": driver_id,
    }
    stored = await service.require_pre_trip_inspection(route, {"id": str(driver_id)})
    assert stored["observation_safe_to_operate"] is True


async def _async_value(value):
    return value
