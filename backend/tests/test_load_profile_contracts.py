from datetime import date

import pytest
from pydantic import ValidationError

from app.models.delivery_model import build_delivery_order_document
from app.models.vehicle_model import build_vehicle_document
from app.schemas.delivery_schema import DeliveryOrderCreate, ParcelLoadProfileInput
from app.schemas.vehicle_schema import VehicleCreate, VehicleLoadProfileInput
from app.services.load_optimization_service import build_vehicle_type_catalog_view
from app.utils.load_profiles import prepare_parcel_load_profile


def parcel_profile(**overrides):
    values = {
        "length_cm": 50,
        "width_cm": 40,
        "height_cm": 30,
        "fragile": True,
        "stackable": False,
        "do_not_tilt": True,
        "service_type": "door_to_door",
    }
    values.update(overrides)
    return ParcelLoadProfileInput(**values)


def vehicle_profile(**overrides):
    values = {
        "profile_code": "MEDIUM_VAN",
        "capacity_m3": 8.5,
        "cargo_length_cm": 320,
        "cargo_width_cm": 170,
        "cargo_height_cm": 175,
        "max_parcels": 120,
        "max_stack_layers": 4,
        "vehicle_max_stack_weight_kg": 750,
        "available_from": "08:00",
        "available_until": "17:00",
    }
    values.update(overrides)
    return VehicleLoadProfileInput(**values)


def test_delivery_document_calculates_volume_and_initializes_load_planning_state():
    payload = DeliveryOrderCreate(
        drop_latitude=6.9271,
        drop_longitude=79.8612,
        parcel_weight=12.5,
        priority="high",
        delivery_date=date(2026, 8, 30),
        delivery_period="first_half",
        load_profile=parcel_profile(),
    )

    document = build_delivery_order_document(payload.model_dump())

    assert document["parcel_volume"] == pytest.approx(0.06)
    assert document["load_profile"]["volume_m3"] == pytest.approx(0.06)
    assert document["load_profile"]["optimizer_priority"] == "express"
    assert document["load_profile"]["time_window_start"] == "08:00"
    assert document["load_profile"]["time_window_end"] == "12:00"
    assert document["load_profile"]["optimization_eligible"] is True
    assert document["load_planning_status"] == "unplanned"
    assert document["active_load_plan_id"] is None


def test_profile_rejects_refrigeration_without_complete_temperature_range():
    with pytest.raises(ValidationError, match="temperature range"):
        parcel_profile(requires_refrigeration=True, temp_min_celsius=2)


def test_profile_rejects_hazardous_parcel_without_hazmat_class():
    with pytest.raises(ValidationError, match="hazmat_class"):
        parcel_profile(hazardous=True)


def test_legacy_volume_is_converted_to_imputed_dimensions_with_warning():
    prepared = prepare_parcel_load_profile(
        {"parcel_weight": 8.0, "parcel_volume": 0.125, "priority": "medium"},
        delivery_period="second_half",
    )

    assert prepared["optimization_eligible"] is True
    assert prepared["dimensions_imputed"] is True
    assert prepared["length_cm"] == pytest.approx(50.0)
    assert prepared["time_window_start"] == "13:00"
    assert "dimensions_imputed" in prepared["data_quality_flags"]


def test_legacy_parcel_without_weight_or_volume_is_explicitly_ineligible():
    prepared = prepare_parcel_load_profile({}, delivery_period="first_half")

    assert prepared["optimization_eligible"] is False
    assert set(prepared["eligibility_reasons"]) == {"parcel_weight_missing", "parcel_dimensions_and_volume_missing"}


def test_vehicle_document_preserves_validated_load_capability_profile():
    payload = VehicleCreate(
        vehicle_code="qa-van-44",
        registration_number="wp cab-4044",
        vehicle_type="diesel_van",
        vehicle_category="van",
        brand="Toyota",
        model="Hiace",
        year=2024,
        fuel_type="diesel",
        payload_capacity_kg=1800,
        load_profile=vehicle_profile(),
    )

    document = build_vehicle_document(payload.model_dump())

    assert document["load_profile"]["profile_code"] == "MEDIUM_VAN"
    assert document["load_profile"]["capacity_m3"] == 8.5
    assert document["load_profile"]["cargo_length_cm"] == 320
    assert document["load_profile"]["available_from"] == "08:00"


def test_vehicle_refrigeration_range_must_fit_inside_valid_bounds():
    with pytest.raises(ValidationError, match="temperature range"):
        vehicle_profile(is_refrigerated=True, temp_min_celsius=8, temp_max_celsius=2)


def test_vehicle_type_catalog_counts_registered_and_active_profiles():
    catalog = [
        {"code": "MEDIUM_VAN", "label": "Medium van", "category": "van"},
        {"code": "MEDIUM_TRUCK", "label": "Medium truck", "category": "truck"},
    ]
    vehicles = [
        {"status": "active", "load_profile": {"profile_code": "MEDIUM_VAN"}},
        {"status": "inactive", "load_profile": {"profile_code": "MEDIUM_VAN"}},
        {"status": "active", "load_profile": {"profile_code": "MEDIUM_TRUCK"}},
        {"status": "active", "load_profile": None},
    ]

    result = build_vehicle_type_catalog_view(catalog, vehicles)

    assert result[0]["registered_vehicle_count"] == 2
    assert result[0]["active_vehicle_count"] == 1
    assert result[1]["registered_vehicle_count"] == 1
    assert result[1]["active_vehicle_count"] == 1
