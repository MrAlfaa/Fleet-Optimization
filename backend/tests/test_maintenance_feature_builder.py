from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.maintenance_feature_service import MaintenanceFeatureBuilder
from app.services.predictive_artifact_registry import EXPECTED_FEATURE_COUNT


NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


def _rules() -> list[dict[str, object]]:
    return [
        {
            "fuel_type": "electric",
            "maintenance_system": system,
            "scheduled_interval_km": service_km,
            "scheduled_interval_days": service_days,
            "simulation_failure_life_km": failure_km,
        }
        for system, service_km, service_days, failure_km in [
            ("battery_system", 30_000, 365, 360_000),
            ("motor_drivetrain", 25_000, 270, 310_000),
            ("charging_system", 20_000, 180, 260_000),
            ("thermal_system", 20_000, 180, 280_000),
            ("braking", 20_000, 180, 190_000),
            ("tires", 15_000, 180, 175_000),
            ("suspension", 25_000, 270, 300_000),
            ("steering", 25_000, 270, 340_000),
            ("electrical", 20_000, 270, 300_000),
        ]
    ]


def test_builder_produces_exact_sensor_free_schema_from_operational_history() -> None:
    feature_columns = MaintenanceFeatureBuilder.default_feature_columns()
    builder = MaintenanceFeatureBuilder(feature_columns=feature_columns, service_rules=_rules())
    vehicle = {
        "year": 2022,
        "vehicle_type": "electric_van",
        "fuel_type": "electric",
        "current_mileage": 48_000,
        "payload_capacity_kg": 1_400,
    }
    trips = [
        {"ended_at": NOW - timedelta(days=3), "trip_distance_km": 120, "parcel_weight_kg": 700, "route_roughness_index": 3.2},
        {"ended_at": NOW - timedelta(days=20), "trip_distance_km": 300, "parcel_weight_kg": 1_120, "route_roughness_index": 2.8},
        {"ended_at": NOW - timedelta(days=50), "trip_distance_km": 500, "parcel_weight_kg": 980, "route_roughness_index": 4.0},
    ]
    maintenance = [
        {
            "service_date": NOW - timedelta(days=40),
            "mileage_at_service": 46_000,
            "maintenance_system": "braking",
            "event_kind": "scheduled_service",
            "status": "completed",
        },
        {
            "service_date": NOW - timedelta(days=200),
            "mileage_at_service": 38_000,
            "maintenance_system": "tires",
            "event_kind": "breakdown",
            "status": "completed",
        },
    ]
    inspections = [
        {
            "created_at": NOW - timedelta(hours=2),
            "observations": {
                "brake_condition": "warning",
                "tire_condition": "normal",
                "powertrain_condition": "normal",
                "dashboard_warning": "amber",
                "charging_or_fuel_issue": "normal",
                "unusual_noise": "normal",
                "unusual_vibration": "warning",
                "vehicle_damage": "normal",
            },
        }
    ]

    result = builder.build(
        vehicle=vehicle,
        trips=trips,
        maintenance_records=maintenance,
        inspections=inspections,
        as_of=NOW,
    )

    assert len(result.features) == EXPECTED_FEATURE_COUNT == 56
    assert list(result.features) == feature_columns
    assert result.features["vehicle_category"] == "van"
    assert result.features["distance_last_7d_km"] == 120
    assert result.features["distance_last_30d_km"] == 420
    assert result.features["distance_last_90d_km"] == 920
    assert result.features["average_load_ratio_30d"] == 0.65
    assert result.features["breakdown_count_365d"] == 1
    assert result.features["brake_condition"] == "warning"
    assert result.features["warning_light_level"] == "warning"
    assert result.features["vibration_level"] == "warning"
    assert result.features["engine_failure_exposure_ratio"] == -1
    assert "in_service_date" in result.defaulted_fields
    assert result.quality_grade in {"fair", "limited"}
    assert result.feature_hash


def test_builder_uses_safe_defaults_for_legacy_vehicle_without_history() -> None:
    builder = MaintenanceFeatureBuilder(
        feature_columns=MaintenanceFeatureBuilder.default_feature_columns(),
        service_rules=_rules(),
    )

    result = builder.build(
        vehicle={
            "year": 2024,
            "vehicle_type": "electric_car",
            "fuel_type": "electric",
            "current_mileage": 1_250,
        },
        trips=[],
        maintenance_records=[],
        inspections=[],
        as_of=NOW,
    )

    assert len(result.features) == 56
    assert result.features["vehicle_category"] == "car"
    assert result.features["trip_distance_km"] == 0
    assert result.features["brake_condition"] == "normal"
    assert result.features["days_since_last_maintenance"] >= 0
    assert set(result.defaulted_fields) >= {
        "vehicle_category",
        "in_service_date",
        "payload_capacity_kg",
        "trip_history",
        "maintenance_history",
        "inspection_history",
    }
    assert result.quality_grade == "limited"


def test_vehicle_age_uses_manufacture_year_not_commissioning_date() -> None:
    builder = MaintenanceFeatureBuilder(
        feature_columns=MaintenanceFeatureBuilder.default_feature_columns(),
        service_rules=_rules(),
    )

    result = builder.build(
        vehicle={
            "year": 2020,
            "in_service_date": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "vehicle_category": "car",
            "vehicle_type": "electric_car",
            "fuel_type": "electric",
            "current_mileage": 10_000,
            "payload_capacity_kg": 450,
        },
        trips=[],
        maintenance_records=[],
        inspections=[],
        as_of=NOW,
    )

    assert result.features["vehicle_age_years"] == 6.0
