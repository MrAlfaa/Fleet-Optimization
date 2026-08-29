from types import SimpleNamespace

import pytest

from app.schemas.predictive_schema import PredictiveRecalculateRequest, PredictionReviewResolveRequest
from app.services import predictive_maintenance_service as service


def test_recalculation_contract_rejects_raw_features() -> None:
    with pytest.raises(ValueError):
        PredictiveRecalculateRequest(trigger="manual_recalculation", sensor_data={"SoC": 80})


def test_review_resolution_contract_is_controlled() -> None:
    assert PredictionReviewResolveRequest(resolution="cleared", notes="Inspected").resolution == "cleared"
    with pytest.raises(ValueError):
        PredictionReviewResolveRequest(resolution="ignored", notes="No")


@pytest.mark.asyncio
async def test_critical_recalculation_reuses_cleared_feature_hash(monkeypatch) -> None:
    feature_result = SimpleNamespace(
        features={"fuel_type": "electric"},
        feature_hash="same-hash",
        defaulted_fields=[],
        quality_grade="good",
        source_ids={},
    )
    artifacts = SimpleNamespace(
        model_version="fleetopt-sensor-free-pm-v1",
        feature_schema_version="3.0",
        metrics={"quality_gate": {"bundle_pass": True}},
    )
    monkeypatch.setattr(service, "build_vehicle_features", lambda vehicle_id: _async_value(feature_result))
    monkeypatch.setattr(service, "get_assessment_eligibility", lambda *_: _async_value({"eligible": True, "blocking_reasons": []}))
    monkeypatch.setattr(service, "_get_vehicle", lambda *_: _async_value({"_id": "vehicle-id", "registration_number": "WP TEST"}))
    monkeypatch.setattr(service.predictive_artifact_registry, "get", lambda: artifacts)
    monkeypatch.setattr(service, "infer_maintenance", lambda *_: {
        "failure_probability": 0.4,
        "failure_probability_30_days": 0.4,
        "failure_probability_2000_km": 0.2,
        "risk_level": "critical",
        "normalized_risk": 3.0,
        "system_risks": [],
        "planning_status": "planning_window_available",
        "planning_window": {"days": {"lower": 1, "upper": 3}},
        "recommended_action": "Review",
        "maintenance_type_name": "braking",
    })
    monkeypatch.setattr(service, "_find_existing_prediction", lambda *_: _async_value(None))
    monkeypatch.setattr(service, "_persist_snapshot", lambda *_, **__: _async_value("snapshot-id"))
    monkeypatch.setattr(service, "_persist_prediction", lambda *_, **__: _async_value({}))
    monkeypatch.setattr(service, "_cache_vehicle_assessment_risk", lambda *_: _async_value(None))
    monkeypatch.setattr(service, "_find_review_for_hash", lambda *_: _async_value({"status": "cleared", "id": "review-id"}))
    monkeypatch.setattr(service, "_apply_prediction_review_state", lambda prediction, review: {**prediction, "review_status": review["status"], "dispatch_hold": False})

    result = await service.recalculate_vehicle_maintenance(
        "64f000000000000000000001",
        {"trigger": "manual_recalculation"},
        {"id": "64f000000000000000000002"},
    )

    assert result["review_status"] == "cleared"
    assert result["dispatch_hold"] is False


async def _async_value(value):
    return value
