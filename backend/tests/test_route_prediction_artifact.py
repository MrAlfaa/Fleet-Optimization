from app.services import route_prediction_service
from app.services.route_artifact_loader_service import get_route_artifact_status


def test_colombo_route_artifact_is_verified_and_loadable() -> None:
    status = get_route_artifact_status(load_model=True)

    assert status["model_version"] == "fleetopt-route-synthetic-v1"
    assert status["integrity_verified"] is True
    assert status["quality_gate_passed"] is True
    assert status["available"] is True
    assert status["feature_count"] == 14


def test_route_prediction_uses_colombo_schema_and_artifact_threshold() -> None:
    frame = route_prediction_service.prepare_route_input({
        "pickup_latitude": 6.9271,
        "pickup_longitude": 79.8612,
        "drop_latitude": 6.884,
        "drop_longitude": 79.886,
        "order_date": "2026-08-29",
        "order_time": "09:00",
        "weather": "Cloudy",
        "traffic_level": "High",
        "vehicle_category": "van",
        "fuel_type": "electric",
        "origin_zone_id": "colombo_central",
        "destination_zone_id": "dehiwala",
        "priority": "high",
    })

    assert list(frame.columns) == [
        "distance_km", "hour", "day_of_week", "month", "is_weekend",
        "road_class", "area_type", "weather", "traffic_level",
        "vehicle_category", "fuel_type", "origin_zone_id",
        "destination_zone_id", "priority",
    ]
    prediction = route_prediction_service.predict_route_segment(frame.iloc[0].to_dict() | {
        "pickup_latitude": 6.9271,
        "pickup_longitude": 79.8612,
        "drop_latitude": 6.884,
        "drop_longitude": 79.886,
    })
    assert prediction["predicted_eta_minutes"] > 0
    assert 0 <= prediction["delay_probability"] <= 1


def test_route_inference_failure_uses_distance_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        route_prediction_service,
        "predict_route_segment",
        lambda _payload: (_ for _ in ()).throw(ValueError("incompatible artifact")),
    )

    prediction, used_model = route_prediction_service.calculate_segment_cost({
        "pickup_latitude": 6.9271,
        "pickup_longitude": 79.8612,
        "drop_latitude": 6.884,
        "drop_longitude": 79.886,
    })

    assert used_model is False
    assert prediction["predicted_eta_minutes"] > 0
