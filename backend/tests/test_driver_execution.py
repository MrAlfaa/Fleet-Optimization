from datetime import datetime, timezone

import pytest
from bson import ObjectId
from pydantic import ValidationError

from app.schemas.driver_schema import (
    DeliveryIncompleteRequest,
    DriverIssueCreate,
    PostTripInspectionRequest,
    PreTripInspectionRequest,
)
from app.services.driver_inspection_service import inspection_blocking_reasons, inspection_model_features
from app.services.driver_service import (
    _mobile_route_summary,
    _mobile_stop,
    _navigation_summary,
    _optimized_delivery_ids,
    calculate_next_delivery_schedule,
    start_driver_stop_navigation,
)
from app.services.live_trip_service import _live_navigation_card
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


def test_mobile_route_summary_exposes_consolidation_and_load_ownership():
    summary = _mobile_route_summary({
        "_id": "route-id",
        "route_code": "ROUTE-PCID-001",
        "route_name": "Consolidated load route",
        "consolidation_id": "PCID202608292H001",
        "route_set_id": "RSET-20260829-001",
        "load_plan_id": "LOADPLAN-20260829-001",
        "load_id": "LOAD-001",
        "delivery_order_ids": ["order-a", "order-b"],
        "status": "dispatched",
    }, total_distance_km=18.4)

    assert summary["consolidation_id"] == "PCID202608292H001"
    assert summary["route_set_id"] == "RSET-20260829-001"
    assert summary["load_plan_id"] == "LOADPLAN-20260829-001"
    assert summary["load_id"] == "LOAD-001"
    assert summary["assigned_stop_count"] == 2


def test_navigation_summary_exposes_current_stop_identity():
    stop_id = ObjectId()

    summary = _navigation_summary(
        {
            "current_stop_id": stop_id,
            "navigation_status": "navigating",
            "navigation_started_at": datetime(2026, 8, 29, 4, 15, tzinfo=timezone.utc),
        },
        [{"_id": stop_id, "order_code": "QA-ORD-001", "customer_name": "QA Customer"}],
    )

    assert summary == {
        "current_stop_id": str(stop_id),
        "current_parcel_code": "QA-ORD-001",
        "current_customer_name": "QA Customer",
        "status": "navigating",
        "started_at": "2026-08-29T04:15:00+00:00",
    }


def test_live_navigation_card_keeps_current_parcel_for_web_monitoring():
    stop_id = ObjectId()

    card = _live_navigation_card(
        {"current_stop_id": stop_id, "navigation_status": "arrived"},
        {"_id": stop_id, "order_code": "QA-ORD-001", "customer_name": "QA Customer"},
    )

    assert card["current_stop_id"] == str(stop_id)
    assert card["current_parcel_code"] == "QA-ORD-001"
    assert card["current_customer_name"] == "QA Customer"
    assert card["status"] == "arrived"


class _NavigationSessionCollection:
    def __init__(self, session):
        self.session = session
        self.update_calls = []

    async def find_one(self, query):
        if query.get("route_id") == self.session["route_id"] and query.get("status") == "active":
            return dict(self.session)
        return None

    async def update_one(self, query, update):
        self.update_calls.append((query, update))
        self.session.update(update["$set"])


@pytest.mark.asyncio
async def test_start_navigation_activates_only_the_next_route_stop(monkeypatch):
    from app.models.trip_model import TRIP_SESSION_COLLECTION
    from app.services import driver_service

    driver_id = ObjectId()
    route_id = ObjectId()
    completed_id = ObjectId()
    next_id = ObjectId()
    later_id = ObjectId()
    route = {
        "_id": route_id,
        "driver_id": driver_id,
        "vehicle_id": ObjectId(),
        "status": "in_progress",
    }
    rows = [
        {"_id": completed_id, "delivery_status": "delivered"},
        {"_id": next_id, "delivery_status": "in_route", "order_code": "QA-NEXT"},
        {"_id": later_id, "delivery_status": "in_route", "order_code": "QA-LATER"},
    ]
    sessions = _NavigationSessionCollection(
        {"_id": ObjectId(), "route_id": route_id, "status": "active"}
    )
    events = []

    async def assigned_route(_):
        return route

    async def ordered_rows(_):
        return rows

    async def create_event(data):
        events.append(data)
        return data

    monkeypatch.setattr(driver_service, "get_assigned_route_raw", assigned_route)
    monkeypatch.setattr(driver_service, "_route_delivery_rows", ordered_rows)
    monkeypatch.setattr(driver_service, "_db", lambda: {TRIP_SESSION_COLLECTION: sessions})
    monkeypatch.setattr(driver_service, "create_trip_event", create_event)

    result = await start_driver_stop_navigation(str(next_id), {"id": str(driver_id)})

    assert result["current_stop_id"] == str(next_id)
    assert result["status"] == "navigating"
    assert len(events) == 1
    assert events[0]["event_type"] == "navigation_started"

    repeated = await start_driver_stop_navigation(str(next_id), {"id": str(driver_id)})
    assert repeated["current_stop_id"] == str(next_id)
    assert len(events) == 1

    with pytest.raises(Exception, match="next route stop"):
        await start_driver_stop_navigation(str(later_id), {"id": str(driver_id)})


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
