from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb

from app.services.maintenance_risk_policy import (
    build_guarded_planning_window,
    classify_normalized_risk,
)
from app.services.predictive_artifact_registry import SensorFreePredictiveArtifacts


def _calibrated_probability(bundle: dict[str, Any], input_value: Any) -> float:
    raw = bundle["model"].predict_proba(input_value)[:, 1]
    probability = float(bundle["calibrator"].predict(raw)[0])
    return min(max(probability, 0.0), 1.0)


def _system_probability(bundle: dict[str, Any], transformed: Any) -> float:
    raw = float(bundle["classifier"].predict_proba(transformed)[:, 1][0])
    probability = float(bundle["calibrator"].predict([raw])[0])
    return min(max(probability, 0.0), 1.0)


def _aft_estimate(model: xgb.Booster, transformed: Any) -> float:
    margin = model.predict(xgb.DMatrix(transformed), output_margin=True)
    return float(np.exp(np.clip(margin, -8.0, 18.0))[0])


def _relative_system_level(normalized_risk: float) -> str:
    return "low" if normalized_risk < 0.5 else "medium" if normalized_risk < 1 else "high" if normalized_risk < 2 else "critical"


def _recommendation(risk_level: str, primary_system: str | None) -> str:
    target = primary_system.replace("_", " ") if primary_system else "vehicle systems"
    if risk_level == "critical":
        return f"Hold dispatch and complete an engineering review of {target}."
    if risk_level == "high":
        return f"Arrange a focused inspection of {target} before the next assignment."
    if risk_level == "medium":
        return f"Monitor {target} and review at the next planned service."
    return "Continue normal operation and scheduled maintenance."


def infer_maintenance(
    features: dict[str, Any],
    artifacts: SensorFreePredictiveArtifacts,
) -> dict[str, Any]:
    missing = [column for column in artifacts.feature_columns if column not in features]
    if missing:
        raise ValueError(f"Predictive feature snapshot is missing: {', '.join(missing)}")
    frame = pd.DataFrame([{column: features[column] for column in artifacts.feature_columns}])
    global_models = artifacts.global_failure_models["models"]
    model_30 = global_models["failure_30_days"]
    model_2000 = global_models["failure_2000_km"]
    probability_30 = _calibrated_probability(model_30, frame)
    probability_2000 = _calibrated_probability(model_2000, frame)
    threshold_30 = float(model_30["operating_threshold"])
    threshold_2000 = float(model_2000["operating_threshold"])
    risk = classify_normalized_risk(
        probability_30,
        threshold_30,
        probability_2000,
        threshold_2000,
    )

    system_bundle = artifacts.system_risk_models
    transformed_systems = system_bundle["preprocessor"].transform(frame)
    system_risks: list[dict[str, Any]] = []
    for system, bundle in system_bundle["models"].items():
        exposure_feature = bundle.get("exposure_feature") or f"{system}_failure_exposure_ratio"
        if float(features.get(exposure_feature, -1.0)) < 0:
            continue
        probability = _system_probability(bundle, transformed_systems)
        threshold = float(bundle["operating_threshold"])
        normalized = probability / threshold if threshold > 0 else 0.0
        system_risks.append({
            "maintenance_system": system,
            "probability": probability,
            "operating_threshold": threshold,
            "normalized_risk": normalized,
            "risk_level": _relative_system_level(normalized),
        })
    system_risks.sort(key=lambda item: (item["normalized_risk"], item["probability"]), reverse=True)
    system_risks = system_risks[:3]
    primary_system = system_risks[0]["maintenance_system"] if system_risks else None

    if risk["risk_level"] in {"high", "critical"}:
        transformed_aft = artifacts.aft_preprocessor.transform(frame)
        raw_days = _aft_estimate(artifacts.aft_days_model, transformed_aft)
        raw_km = _aft_estimate(artifacts.aft_km_model, transformed_aft)
    else:
        raw_days = None
        raw_km = None
    planning = build_guarded_planning_window(
        str(risk["risk_level"]),
        raw_days,
        raw_km,
        artifacts.planning_intervals,
    )
    return {
        "failure_probability_30_days": probability_30,
        "failure_probability_2000_km": probability_2000,
        "operating_threshold_30_days": threshold_30,
        "operating_threshold_2000_km": threshold_2000,
        "normalized_risk": risk["normalized_risk"],
        "risk_level": risk["risk_level"],
        "system_risks": system_risks,
        **planning,
        "recommended_action": _recommendation(str(risk["risk_level"]), primary_system),
        # Compatibility aliases for older web and report adapters.
        "failure_probability": probability_30,
        "maintenance_type_name": primary_system,
    }
