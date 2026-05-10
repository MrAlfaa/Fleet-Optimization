from datetime import datetime, timedelta, timezone
from typing import Any


def normalize_probability(value: Any) -> float:
    try:
        probability = float(value)
    except (TypeError, ValueError):
        return 0.0
    if probability > 1:
        probability = probability / 100
    return max(0.0, min(probability, 1.0))


def risk_level_from_probability(probability: float) -> str:
    probability = normalize_probability(probability)
    if probability >= 0.70:
        return "critical"
    if probability >= 0.40:
        return "high"
    if probability >= 0.20:
        return "medium"
    return "low"


def recommended_action_from_risk(risk_level: str, maintenance_type_name: str | None = None) -> str:
    target = f" for {maintenance_type_name}" if maintenance_type_name and maintenance_type_name != "Unknown" else ""
    if risk_level == "critical":
        return f"Immediate inspection required before dispatch{target}."
    if risk_level == "high":
        return f"Schedule maintenance soon and avoid heavy route assignment{target}."
    if risk_level == "medium":
        return f"Schedule inspection during next maintenance window{target}."
    return "Continue normal operation and monitor periodically."


def calculate_next_maintenance_date(
    base_date: datetime | None,
    predicted_rul: float | None,
    rul_unit: str | None,
) -> datetime | None:
    if predicted_rul is None:
        return None

    base = base_date or datetime.now(timezone.utc)
    unit = (rul_unit or "hours").lower()
    if unit in {"hour", "hours", "h"}:
        return base + timedelta(hours=float(predicted_rul))
    if unit in {"day", "days", "d"}:
        return base + timedelta(days=float(predicted_rul))
    if unit in {"week", "weeks", "w"}:
        return base + timedelta(weeks=float(predicted_rul))
    return base + timedelta(hours=float(predicted_rul))


def map_maintenance_type_to_part(maintenance_type_name: str | None) -> str | None:
    if not maintenance_type_name:
        return None

    value = maintenance_type_name.lower()
    if "battery" in value:
        return "Battery Pack"
    if "motor" in value or "drivetrain" in value or "drive" in value:
        return "Electric Motor"
    if "brake" in value:
        return "Brake Pads"
    if "tire" in value or "tyre" in value:
        return "Tires"
    if "suspension" in value:
        return "Suspension System"
    if "cool" in value or "thermal" in value:
        return "Thermal Management System"
    return None
