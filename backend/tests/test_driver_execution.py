from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.driver_schema import (
    DeliveryIncompleteRequest,
    DriverIssueCreate,
    PostTripInspectionRequest,
    PreTripInspectionRequest,
)
from app.services.driver_inspection_service import inspection_blocking_reasons, inspection_model_features
from app.services.driver_service import _mobile_stop, _optimized_delivery_ids, calculate_next_delivery_schedule
from scripts.seed_users import DEMO_USERS


def test_incomplete_other_requires_details():
    with pytest.raises(ValidationError):
        DeliveryIncompleteRequest(reason="other", idempotency_key="1234567890abcdef")


def test_incomplete_accepts_documented_weather_reason():
    request = DeliveryIncompleteRequest(reason="weather_or_route_issue", idempotency_key="1234567890abcdef")
    assert request.reason == "weather_or_route_issue"


def test_issue_category_is_restricted():
    with pytest.raises(ValidationError):
        DriverIssueCreate(title="Issue", message="Details", category="unknown_system")


def test_missing_schedule_defaults_to_next_day_0900_colombo():
    now = datetime(2026, 8, 16, 4, 0, tzinfo=timezone.utc)  # 09:30 in Colombo
    result = calculate_next_delivery_schedule(None, now)
    assert result == datetime(2026, 8, 17, 3, 30, tzinfo=timezone.utc)


def test_existing_schedule_preserves_local_time_next_day():
    scheduled = datetime(2026, 8, 16, 8, 15, tzinfo=timezone.utc)
    assert calculate_next_delivery_schedule(scheduled) == datetime(2026, 8, 17, 8, 15, tzinfo=timezone.utc)


def test_driver_route_supports_structured_stop_order():
    route = {
        "delivery_order_ids": ["order-a", "order-b"],
        "optimized_stop_order": [
            {"type": "depot"},
            {"type": "delivery", "order_id": "order-b"},
            {"type": "delivery", "order_id": "order-a"},
        ],
    }

    assert _optimized_delivery_ids(route) == ["order-b", "order-a"]


def test_driver_route_supports_legacy_integer_stop_order():
    route = {
        "delivery_order_ids": ["order-a", "order-b", "order-c"],
        "optimized_stop_order": [0, 2, 1, 3, 0],
    }

    assert _optimized_delivery_ids(route) == ["order-b", "order-a", "order-c"]


def test_driver_route_falls_back_when_optimized_order_is_malformed():
    route = {
        "delivery_order_ids": ["order-a", "order-b"],
        "optimized_stop_order": [None, True, {"type": "delivery"}, 99],
    }

    assert _optimized_delivery_ids(route) == ["order-a", "order-b"]


def test_mobile_stop_includes_actionable_parcel_details():
    stop = _mobile_stop(
        {
            "_id": "order-a",
            "order_code": "ORD-001",
            "customer_name": "Colombo Customer",
            "customer_phone": "0771234567",
            "drop_address": "Union Place, Colombo",
            "drop_latitude": 6.9147,
            "drop_longitude": 79.8729,
            "parcel_weight": 12.5,
            "load_profile": {
                "length_cm": 60,
                "width_cm": 40,
                "height_cm": 35,
                "fragile": True,
                "two_person_lift": False,
                "do_not_tilt": True,
                "requires_refrigeration": False,
                "hazardous": False,
            },
        },
        3,
        {"delivery_order_ids": ["order-a"], "total_predicted_eta_minutes": 20},
    )

    assert stop["parcel_code"] == "ORD-001"
    assert stop["parcel_weight_kg"] == 12.5
    assert stop["dimensions_cm"] == {"length": 60.0, "width": 40.0, "height": 35.0}
    assert stop["handling"] == ["Fragile", "Do not tilt"]


def test_seeded_demo_driver_has_mobile_enrollment_username():
    driver = next(user for user in DEMO_USERS if user["role"] == "driver")

    assert driver["username"] == "driver.demo"


def test_pre_trip_inspection_rejects_uncontrolled_condition_value():
    with pytest.raises(ValidationError):
        PreTripInspectionRequest(
            odometer=42000,
            battery_soc=72,
            tire_condition="looks okay",
            brake_condition="normal",
            charging_condition="normal",
            vehicle_damage="none",
            dashboard_warning="none",
            unusual_noise="none",
            unusual_vibration="none",
        )


def test_pre_trip_safety_rules_block_critical_observations():
    payload = PreTripInspectionRequest(
        odometer=42000,
        battery_soc=72,
        tire_condition="damaged",
        brake_condition="warning_light",
        charging_condition="normal",
        vehicle_damage="none",
        dashboard_warning="red",
        unusual_noise="none",
        unusual_vibration="none",
    )

    assert inspection_blocking_reasons(payload.model_dump()) == [
        "Tire damage requires inspection",
        "Brake warning requires inspection",
        "A red dashboard warning is active",
    ]


def test_driver_observations_do_not_become_invented_model_measurements():
    payload = PreTripInspectionRequest(
        odometer=42000,
        battery_soc=72,
        tire_condition="worn",
        brake_condition="noisy",
        charging_condition="intermittent",
        vehicle_damage="minor",
        dashboard_warning="amber",
        unusual_noise="mild",
        unusual_vibration="mild",
    )

    assert inspection_model_features(payload.model_dump()) == {}


def test_post_trip_inspection_requires_end_mileage_not_below_start():
    payload = PostTripInspectionRequest(
        ending_odometer=41999,
        ending_battery_soc=45,
        tire_condition_change="none",
        brake_condition_change="none",
        charging_problem="none",
        vehicle_damage="none",
        dashboard_warning="none",
        unusual_noise="none",
        unusual_vibration="none",
    )

    with pytest.raises(ValueError, match="Ending odometer"):
        payload.validate_against_starting_odometer(42000)
