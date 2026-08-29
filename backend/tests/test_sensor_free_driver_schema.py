import pytest
from pydantic import ValidationError

from app.schemas.driver_schema import PostTripInspectionRequest, PreTripInspectionRequest
from app.services.driver_inspection_service import inspection_blocking_reasons


def test_non_ev_pre_trip_does_not_require_battery_soc() -> None:
    payload = PreTripInspectionRequest(
        odometer=42000,
        tire_condition="normal",
        brake_condition="normal",
        powertrain_condition="normal",
        dashboard_warning="none",
        charging_or_fuel_issue="none",
        unusual_noise="none",
        vibration_level="none",
        vehicle_damage="none",
    )
    assert payload.battery_soc is None


def test_pre_trip_rejects_uncontrolled_powertrain_condition() -> None:
    with pytest.raises(ValidationError):
        PreTripInspectionRequest(
            odometer=42000,
            tire_condition="normal",
            brake_condition="normal",
            powertrain_condition="sounds strange",
            dashboard_warning="none",
            charging_or_fuel_issue="none",
            unusual_noise="none",
            vibration_level="none",
            vehicle_damage="none",
        )


def test_critical_powertrain_observation_blocks() -> None:
    payload = PostTripInspectionRequest(
        ending_odometer=42100,
        tire_condition="normal",
        brake_condition="normal",
        powertrain_condition="critical",
        dashboard_warning="red",
        charging_or_fuel_issue="critical",
        unusual_noise="severe",
        vibration_level="severe",
        vehicle_damage="none",
    )
    reasons = inspection_blocking_reasons(payload.model_dump())
    assert "Powertrain condition requires inspection" in reasons
    assert "Charging or fuel system requires inspection" in reasons
