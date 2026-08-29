from bson import ObjectId

from app.services.predictive_maintenance_service import _public_prediction, _public_review


def test_prediction_public_view_adds_vehicle_identity_and_hides_raw_features() -> None:
    result = _public_prediction(
        {"_id": ObjectId(), "vehicle_id": ObjectId(), "risk_level": "high", "input_features": {"secret": 1}},
        {"registration_number": "WP CAA-1000", "vehicle_code": "FLT-1"},
    )
    assert result["vehicle_registration"] == "WP CAA-1000"
    assert result["vehicle_code"] == "FLT-1"
    assert "input_features" not in result


def test_review_public_view_includes_risk_and_top_systems_with_serialized_ids() -> None:
    review_id, prediction_id, vehicle_id = ObjectId(), ObjectId(), ObjectId()
    result = _public_review(
        {"_id": review_id, "vehicle_id": vehicle_id, "prediction_id": prediction_id, "status": "pending"},
        {"registration_number": "WP CAA-1000", "vehicle_code": "FLT-1"},
        {"risk_level": "critical", "maintenance_type_name": "braking", "system_risks": [
            {"maintenance_system": "braking"}, {"maintenance_system": "tires"},
            {"maintenance_system": "steering"}, {"maintenance_system": "suspension"},
        ]},
    )
    assert result["id"] == str(review_id)
    assert result["vehicle_id"] == str(vehicle_id)
    assert result["vehicle_registration"] == "WP CAA-1000"
    assert result["risk_level"] == "critical"
    assert result["maintenance_system"] == "braking"
    assert len(result["system_risks"]) == 3
