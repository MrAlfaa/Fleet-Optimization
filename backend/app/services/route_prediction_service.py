import re
import logging
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from app.services.route_artifact_loader_service import (
    RouteArtifactUnavailableError,
    get_route_artifact_status,
    load_route_metrics,
    load_route_model_bundle,
    load_route_schema,
)
from app.utils.geo_utils import haversine_distance_km
from app.utils.route_utils import calculate_route_cost, delay_risk_level_from_probability, priority_penalty


ROUTE_ALLOWED_ROLES = ["admin", "fleet_manager", "route_planner"]
ROUTE_DRIVER_VIEW_ROLES = ["admin", "fleet_manager", "route_planner", "driver"]
logger = logging.getLogger(__name__)


def get_model_status() -> dict[str, Any]:
    return get_route_artifact_status(load_model=True)


def get_model_metrics() -> dict[str, Any]:
    return load_route_metrics() or {}


def _clean_column_name(column: str) -> str:
    cleaned = str(column).strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("_")


def _feature_columns(bundle: dict[str, Any]) -> list[str]:
    if bundle.get("feature_columns"):
        return list(bundle["feature_columns"])
    schema = load_route_schema() or {}
    return list(schema.get("feature_columns") or [])


def prepare_route_input(input_data: dict[str, Any]) -> pd.DataFrame:
    bundle = load_route_model_bundle()
    feature_columns = _feature_columns(bundle)
    if not feature_columns:
        raise RouteArtifactUnavailableError(
            "Route prediction model schema is unavailable",
            {"artifact_path": get_route_artifact_status()["artifact_path"]},
        )

    normalized = {
        "weather": input_data.get("weather") or "Cloudy",
        "traffic_level": input_data.get("traffic_level") or input_data.get("traffic") or "Medium",
        "vehicle_category": input_data.get("vehicle_category") or input_data.get("vehicle_type") or "van",
        "fuel_type": input_data.get("fuel_type") or "electric",
        "area_type": input_data.get("area_type") or input_data.get("area") or "urban",
        "road_class": input_data.get("road_class") or "primary",
        "origin_zone_id": input_data.get("origin_zone_id") or "colombo_central",
        "destination_zone_id": input_data.get("destination_zone_id") or "colombo_central",
        "priority": input_data.get("priority") or "medium",
    }
    normalized.update({k: v for k, v in input_data.items() if v is not None})

    distance_km = haversine_distance_km(
        float(input_data["pickup_latitude"]),
        float(input_data["pickup_longitude"]),
        float(input_data["drop_latitude"]),
        float(input_data["drop_longitude"]),
    )
    normalized["distance_km"] = distance_km

    date_value = input_data.get("order_date")
    time_value = input_data.get("order_time")
    if date_value and time_value:
        dt = pd.to_datetime(f"{date_value} {time_value}", errors="coerce")
    elif date_value:
        dt = pd.to_datetime(date_value, errors="coerce")
    else:
        dt = pd.to_datetime(datetime.utcnow())
    if pd.isna(dt):
        dt = pd.to_datetime(datetime.utcnow())
    normalized["hour"] = int(dt.hour)
    normalized["day_of_week"] = int(dt.dayofweek)
    normalized["month"] = int(dt.month)
    normalized["is_weekend"] = int(dt.dayofweek in [5, 6])

    frame = pd.DataFrame([normalized])
    frame.columns = [_clean_column_name(column) for column in frame.columns]
    for column in feature_columns:
        if column not in frame.columns:
            frame[column] = np.nan
    return frame[feature_columns]


def predict_route_segment(input_data: dict[str, Any]) -> dict[str, Any]:
    bundle = load_route_model_bundle()
    eta_model = bundle.get("eta_model")
    delay_model = bundle.get("delay_model")
    if eta_model is None or delay_model is None:
        raise RouteArtifactUnavailableError(
            "Route prediction model bundle is missing required models",
            {"required_keys": ["eta_model", "delay_model"], "available_keys": sorted(bundle.keys())},
        )

    frame = prepare_route_input(input_data)
    eta = max(float(eta_model.predict(frame)[0]), 0)
    if hasattr(delay_model, "predict_proba"):
        delay_probability = float(delay_model.predict_proba(frame)[0][1])
    else:
        delay_probability = float(delay_model.predict(frame)[0])
    delay_probability = max(0.0, min(delay_probability, 1.0))
    threshold = float(bundle.get("delay_threshold") or (load_route_schema() or {}).get("delay_threshold") or 0.5)
    delay_prediction = int(delay_probability >= threshold)
    risk_level = delay_risk_level_from_probability(delay_probability)
    distance_km = haversine_distance_km(
        input_data["pickup_latitude"],
        input_data["pickup_longitude"],
        input_data["drop_latitude"],
        input_data["drop_longitude"],
    )
    priority_adjustment = priority_penalty(input_data.get("priority"))
    cost = calculate_route_cost(eta, delay_probability) * (1 + priority_adjustment)

    return {
        "distance_km": round(distance_km, 3),
        "predicted_eta_minutes": round(eta, 2),
        "delay_probability": round(delay_probability, 4),
        "delay_prediction": delay_prediction,
        "delay_risk_level": risk_level,
        "route_cost_score": round(max(cost, 1), 2),
    }


def predict_route_segments_batch(segment_list: list[dict[str, Any]]) -> dict[str, Any]:
    results = [predict_route_segment(segment) for segment in segment_list]
    return {"count": len(results), "items": results}


def fallback_segment_prediction(input_data: dict[str, Any]) -> dict[str, Any]:
    distance_km = haversine_distance_km(
        input_data["pickup_latitude"],
        input_data["pickup_longitude"],
        input_data["drop_latitude"],
        input_data["drop_longitude"],
    )
    eta = max(distance_km / 28 * 60, 1)
    delay_probability = 0.25
    return {
        "distance_km": round(distance_km, 3),
        "predicted_eta_minutes": round(eta, 2),
        "delay_probability": delay_probability,
        "delay_prediction": 0,
        "delay_risk_level": delay_risk_level_from_probability(delay_probability),
        "route_cost_score": calculate_route_cost(eta, delay_probability),
    }


def calculate_segment_cost(input_data: dict[str, Any], use_ml_cost: bool = True) -> tuple[dict[str, Any], bool]:
    if not use_ml_cost:
        return fallback_segment_prediction(input_data), False
    try:
        return predict_route_segment(input_data), True
    except Exception as exc:  # The optimizer must remain usable when an artifact or inference step fails.
        logger.warning("Route model inference failed; using distance fallback: %s", exc)
        return fallback_segment_prediction(input_data), False
