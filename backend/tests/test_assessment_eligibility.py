from __future__ import annotations

from app.services.maintenance_eligibility_service import evaluate_assessment_eligibility
from app.schemas.vehicle_schema import VehicleCreate
from app.models.vehicle_model import build_vehicle_document


COMPLETE_VEHICLE = {
    "vehicle_code": "FLT-101",
    "registration_number": "WP CAA-1010",
    "vehicle_category": "van",
    "fuel_type": "electric",
    "year": 2025,
    "in_service_date": "2025-01-10T00:00:00Z",
    "payload_capacity_kg": 1200,
    "current_mileage": 250,
    "onboarding_type": "brand_new",
}


def test_brand_new_vehicle_builds_history_before_first_assessment() -> None:
    result = evaluate_assessment_eligibility(
        vehicle=COMPLETE_VEHICLE,
        commissioning_passed=True,
        completed_trip_count=3,
        recorded_distance_km=68,
        imported_history_count=0,
        latest_feature_hash=None,
        current_prediction_hash=None,
    )

    assert result["eligible"] is False
    assert result["status"] == "building_history"
    assert result["requirements"]["completed_trips"]["current"] == 3
    assert result["requirements"]["recorded_distance_km"]["current"] == 68
    assert "Complete 2 more trip(s)" in result["blocking_reasons"]


def test_existing_vehicle_with_imported_history_becomes_ready_after_commissioning() -> None:
    result = evaluate_assessment_eligibility(
        vehicle={**COMPLETE_VEHICLE, "onboarding_type": "existing_fleet"},
        commissioning_passed=True,
        completed_trip_count=0,
        recorded_distance_km=0,
        imported_history_count=2,
        latest_feature_hash="feature-new",
        current_prediction_hash=None,
    )

    assert result["eligible"] is True
    assert result["status"] == "ready_for_assessment"
    assert result["requirements"]["history_evidence"]["complete"] is True


def test_same_feature_snapshot_is_current_and_does_not_need_recalculation() -> None:
    result = evaluate_assessment_eligibility(
        vehicle=COMPLETE_VEHICLE,
        commissioning_passed=True,
        completed_trip_count=5,
        recorded_distance_km=140,
        imported_history_count=0,
        latest_feature_hash="same-hash",
        current_prediction_hash="same-hash",
    )

    assert result["eligible"] is True
    assert result["status"] == "assessment_current"
    assert result["has_new_data"] is False


def test_incomplete_profile_is_reported_before_history_requirements() -> None:
    result = evaluate_assessment_eligibility(
        vehicle={**COMPLETE_VEHICLE, "payload_capacity_kg": None},
        commissioning_passed=False,
        completed_trip_count=0,
        recorded_distance_km=0,
        imported_history_count=0,
        latest_feature_hash=None,
        current_prediction_hash=None,
    )

    assert result["status"] == "profile_incomplete"
    assert result["missing_profile_fields"] == ["payload_capacity_kg"]


def test_new_vehicle_schema_defaults_to_inactive_existing_fleet_onboarding() -> None:
    payload = VehicleCreate(
        vehicle_code="FLT-102",
        registration_number="WP CAA-1020",
        vehicle_type="diesel_van",
        vehicle_category="van",
        brand="Toyota",
        model="Hiace",
        year=2024,
        fuel_type="diesel",
        in_service_date="2024-01-10T00:00:00Z",
        payload_capacity_kg=1200,
    )

    assert payload.onboarding_type == "existing_fleet"
    assert payload.status == "inactive"
    assert build_vehicle_document(payload.model_dump())["status"] == "inactive"
