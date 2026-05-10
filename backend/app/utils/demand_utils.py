from datetime import datetime, timezone
from typing import Any
import math

import pandas as pd


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        result = float(value)
        return default if math.isnan(result) else result
    except (TypeError, ValueError):
        return default


def parse_forecast_date(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Invalid forecast date: {value}")
    if parsed.tzinfo is None:
        return parsed.to_pydatetime().replace(tzinfo=timezone.utc)
    return parsed.to_pydatetime()


def normalize_demand_level(value: float) -> str:
    predicted = safe_float(value)
    if predicted >= 80:
        return "very_high"
    if predicted >= 50:
        return "high"
    if predicted >= 25:
        return "medium"
    return "low"


def estimate_required_vehicles(predicted_demand: float, orders_per_vehicle: int = 25) -> int:
    if orders_per_vehicle <= 0:
        orders_per_vehicle = 25
    return max(1, math.ceil(max(safe_float(predicted_demand), 0) / orders_per_vehicle))


def recommended_action_from_demand_level(level: str) -> str:
    normalized = str(level or "low").lower()
    actions = {
        "low": "Normal fleet allocation is sufficient.",
        "medium": "Monitor demand and maintain standard delivery capacity.",
        "high": "Allocate additional vehicle capacity for this zone.",
        "very_high": "Prioritize route planning and assign additional vehicles immediately.",
    }
    return actions.get(normalized, actions["low"])


def zone_display_fields(zone_id: str) -> dict[str, str | None]:
    if "_" not in zone_id:
        return {"state": None, "city": None, "zone_name": zone_id}
    state, raw_city = zone_id.split("_", 1)
    city = raw_city.replace("_", " ").title()
    return {"state": state.upper(), "city": city, "zone_name": f"{city} ({state.upper()})"}


def _read_value(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in row and not pd.isna(row[key]):
            return row[key]
    return default


def standardize_forecast_record(row: dict[str, Any], horizon_days: int | None = None) -> dict[str, Any]:
    forecast_date = parse_forecast_date(_read_value(row, "ds", "forecast_date"))
    graph_forecast = safe_float(_read_value(row, "final_graph_enhanced_forecast", "graph_enhanced_yhat", "graph_enhanced_forecast"))
    predicted_demand = safe_float(_read_value(row, "predicted_demand", default=graph_forecast), default=graph_forecast)
    baseline = safe_float(_read_value(row, "baseline_prophet_forecast", "baseline_yhat", "yhat"), default=0.0)
    return {
        "zone_id": str(row["zone_id"]),
        "forecast_date": forecast_date,
        "baseline_prophet_forecast": baseline,
        "graph_enhanced_forecast": graph_forecast,
        "predicted_demand": predicted_demand,
        "forecast_horizon_days": horizon_days,
        "model_type": "graph_enhanced_prophet",
    }


def standardize_planning_record(row: dict[str, Any]) -> dict[str, Any]:
    forecast_date = parse_forecast_date(_read_value(row, "ds", "forecast_date"))
    predicted_demand = safe_float(_read_value(row, "predicted_demand", "final_graph_enhanced_forecast"))
    level = str(_read_value(row, "demand_level", default=normalize_demand_level(predicted_demand))).lower().replace(" ", "_")
    if level not in {"low", "medium", "high", "very_high"}:
        level = normalize_demand_level(predicted_demand)
    vehicles = int(safe_float(_read_value(row, "estimated_required_vehicles"), default=estimate_required_vehicles(predicted_demand)))
    return {
        "zone_id": str(row["zone_id"]),
        "forecast_date": forecast_date,
        "predicted_demand": predicted_demand,
        "demand_level": level,
        "estimated_required_vehicles": max(1, vehicles),
        "recommended_action": recommended_action_from_demand_level(level),
    }
