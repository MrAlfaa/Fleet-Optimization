from __future__ import annotations

import math
from typing import Any


MAX_PLANNING_DAYS = 1_825
MAX_PLANNING_KM = 250_000


def classify_normalized_risk(
    probability_30_days: float,
    threshold_30_days: float,
    probability_2000_km: float,
    threshold_2000_km: float,
) -> dict[str, float | str]:
    if threshold_30_days <= 0 or threshold_2000_km <= 0:
        raise ValueError("Artifact operating thresholds must be positive")

    normalized = max(
        max(float(probability_30_days), 0.0) / threshold_30_days,
        max(float(probability_2000_km), 0.0) / threshold_2000_km,
    )
    level = "low" if normalized < 0.5 else "medium" if normalized < 1 else "high" if normalized < 2 else "critical"
    return {"normalized_risk": normalized, "risk_level": level}


def _finite_positive(value: float | None) -> bool:
    return value is not None and math.isfinite(float(value)) and float(value) >= 0


def _bounded_range(raw_value: float, interval: dict[str, Any], maximum: int) -> dict[str, int]:
    lower_multiplier = float(interval["lower_multiplier"])
    upper_multiplier = float(interval["upper_multiplier"])
    if lower_multiplier < 0 or upper_multiplier < lower_multiplier:
        raise ValueError("Invalid planning interval multipliers")
    lower = min(maximum, max(0, round(raw_value * lower_multiplier)))
    upper = min(maximum, max(lower, round(raw_value * upper_multiplier)))
    return {"lower": lower, "upper": upper}


def build_guarded_planning_window(
    risk_level: str,
    raw_days: float | None,
    raw_km: float | None,
    planning_intervals: dict[str, Any],
) -> dict[str, Any]:
    if risk_level in {"low", "medium"}:
        return {"planning_status": "no_near_term_failure_indicated", "planning_window": None}
    if not _finite_positive(raw_days) or not _finite_positive(raw_km):
        return {"planning_status": "estimate_withheld", "planning_window": None}

    try:
        window = {
            "days": _bounded_range(float(raw_days), planning_intervals["days"], MAX_PLANNING_DAYS),
            "km": _bounded_range(float(raw_km), planning_intervals["km"], MAX_PLANNING_KM),
        }
    except (KeyError, TypeError, ValueError):
        return {"planning_status": "estimate_withheld", "planning_window": None}
    return {"planning_status": "planning_window_available", "planning_window": window}
