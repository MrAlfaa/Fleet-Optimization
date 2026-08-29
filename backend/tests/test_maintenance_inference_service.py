from types import SimpleNamespace

import numpy as np

from app.services.maintenance_inference_service import infer_maintenance


class FakeBinaryModel:
    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, frame):
        return np.array([[1 - self.probability, self.probability] for _ in range(len(frame))])


class FakeCalibrator:
    def predict(self, values):
        return np.asarray(values)


class FakePreprocessor:
    def transform(self, frame):
        return np.zeros((len(frame), 2))


def test_inference_uses_artifact_thresholds_and_only_applicable_systems(monkeypatch) -> None:
    features = {
        "fuel_type": "diesel",
        "braking_failure_exposure_ratio": 0.8,
        "engine_failure_exposure_ratio": 0.7,
        "battery_system_failure_exposure_ratio": -1.0,
    }
    global_models = {
        "failure_30_days": {
            "model": FakeBinaryModel(0.18),
            "calibrator": FakeCalibrator(),
            "operating_threshold": 0.12,
        },
        "failure_2000_km": {
            "model": FakeBinaryModel(0.04),
            "calibrator": FakeCalibrator(),
            "operating_threshold": 0.08,
        },
    }
    system_models = {
        name: {
            "classifier": FakeBinaryModel(probability),
            "calibrator": FakeCalibrator(),
            "operating_threshold": threshold,
            "exposure_feature": f"{name}_failure_exposure_ratio",
        }
        for name, probability, threshold in [
            ("braking", 0.60, 0.30),
            ("engine", 0.20, 0.25),
            ("battery_system", 0.99, 0.10),
        ]
    }
    artifacts = SimpleNamespace(
        feature_columns=list(features),
        global_failure_models={"models": global_models},
        system_risk_models={"preprocessor": FakePreprocessor(), "models": system_models},
        aft_preprocessor=FakePreprocessor(),
        aft_days_model=object(),
        aft_km_model=object(),
        planning_intervals={
            "days": {"lower_multiplier": 0.5, "upper_multiplier": 1.5},
            "km": {"lower_multiplier": 0.5, "upper_multiplier": 1.5},
        },
    )
    monkeypatch.setattr(
        "app.services.maintenance_inference_service._aft_estimate",
        lambda model, transformed: 100.0 if model is artifacts.aft_days_model else 10_000.0,
    )

    result = infer_maintenance(features, artifacts)

    assert result["failure_probability_30_days"] == 0.18
    assert result["failure_probability_2000_km"] == 0.04
    assert result["normalized_risk"] == 1.5
    assert result["risk_level"] == "high"
    assert [item["maintenance_system"] for item in result["system_risks"]] == ["braking", "engine"]
    assert result["planning_window"] == {
        "days": {"lower": 50, "upper": 150},
        "km": {"lower": 5_000, "upper": 15_000},
    }
    assert "raw_days" not in result
    assert result["failure_probability"] == result["failure_probability_30_days"]
    assert result["maintenance_type_name"] == "braking"


def test_low_risk_does_not_expose_planning_values(monkeypatch) -> None:
    features = {"fuel_type": "electric", "battery_system_failure_exposure_ratio": 0.2}
    bundle = {
        name: {
            "model": FakeBinaryModel(0.01),
            "calibrator": FakeCalibrator(),
            "operating_threshold": 0.10,
        }
        for name in ("failure_30_days", "failure_2000_km")
    }
    artifacts = SimpleNamespace(
        feature_columns=list(features),
        global_failure_models={"models": bundle},
        system_risk_models={"preprocessor": FakePreprocessor(), "models": {}},
        aft_preprocessor=FakePreprocessor(),
        aft_days_model=object(),
        aft_km_model=object(),
        planning_intervals={},
    )
    monkeypatch.setattr("app.services.maintenance_inference_service._aft_estimate", lambda *_: 999.0)

    result = infer_maintenance(features, artifacts)

    assert result["risk_level"] == "low"
    assert result["planning_status"] == "no_near_term_failure_indicated"
    assert result["planning_window"] is None
