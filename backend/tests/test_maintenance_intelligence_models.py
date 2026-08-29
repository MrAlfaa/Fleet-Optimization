from datetime import datetime, timezone

from bson import ObjectId

from app.models.maintenance_intelligence_model import (
    build_feature_snapshot_document,
    build_prediction_review_document,
)
from app.models.maintenance_model import build_maintenance_document
from app.models.predictive_model import build_prediction_document
from app.models.vehicle_model import build_vehicle_document


def test_snapshot_and_review_documents_preserve_auditable_identity() -> None:
    vehicle_id = ObjectId()
    prediction_id = ObjectId()
    features = {"fuel_type": "diesel", "current_odometer_km": 82_500.0}
    snapshot = build_feature_snapshot_document(
        {
            "vehicle_id": vehicle_id,
            "trigger": "manual_recalculation",
            "features": features,
            "feature_hash": "abc123",
            "source_ids": {"maintenance_record_ids": [ObjectId()]},
            "defaulted_fields": ["route_roughness"],
            "quality_grade": "fair",
            "model_version": "fleetopt-sensor-free-pm-v1",
            "feature_schema_version": "3.0",
        }
    )
    review = build_prediction_review_document(
        {
            "vehicle_id": vehicle_id,
            "prediction_id": prediction_id,
            "feature_hash": "abc123",
            "status": "pending",
            "created_by": ObjectId(),
        }
    )

    assert snapshot["features"] == features
    assert snapshot["feature_hash"] == "abc123"
    assert snapshot["created_at"].tzinfo is not None
    assert review["prediction_id"] == prediction_id
    assert review["status"] == "pending"
    assert review["resolution"] is None


def test_vehicle_and_maintenance_documents_accept_canonical_sensor_free_fields() -> None:
    in_service_date = datetime(2023, 1, 10, tzinfo=timezone.utc)
    vehicle = build_vehicle_document(
        {
            "vehicle_code": "flt-1",
            "registration_number": "wp cab-1000",
            "vehicle_type": "electric_van",
            "vehicle_category": "van",
            "brand": "Test",
            "model": "Cargo",
            "year": 2022,
            "fuel_type": "electric",
            "in_service_date": in_service_date,
            "payload_capacity_kg": 1_400,
        }
    )
    maintenance = build_maintenance_document(
        {
            "vehicle_id": ObjectId(),
            "part_name": "Brake Pads",
            "maintenance_type": "corrective",
            "maintenance_system": "braking",
            "event_kind": "corrective_repair",
            "issue_type": "Wear",
            "service_date": datetime.now(timezone.utc),
            "mileage_at_service": 10_000,
        },
        ObjectId(),
    )

    assert vehicle["vehicle_category"] == "van"
    assert vehicle["in_service_date"] == in_service_date
    assert vehicle["payload_capacity_kg"] == 1_400
    assert maintenance["maintenance_system"] == "braking"
    assert maintenance["event_kind"] == "corrective_repair"


def test_prediction_document_preserves_defaulted_feature_audit_fields() -> None:
    prediction = build_prediction_document({
        "vehicle_id": ObjectId(), "input_source": "manual_recalculation", "input_features": {},
        "failure_prediction": 0, "failure_probability": 0.02, "risk_level": "low",
        "recommended_action": "Continue normal operation.",
        "defaulted_fields": ["route_roughness", "trip_history"],
    })
    assert prediction["defaulted_fields"] == ["route_roughness", "trip_history"]
