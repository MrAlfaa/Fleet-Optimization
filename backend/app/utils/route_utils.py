from datetime import datetime, timezone
from uuid import uuid4


DELIVERY_PRIORITIES = {"low", "medium", "high", "urgent"}
DELIVERY_STATUSES = {"pending", "assigned", "in_route", "delivered", "failed", "cancelled"}
ROUTE_STATUSES = {"draft", "optimized", "dispatched", "in_progress", "completed", "cancelled"}
ROUTE_RUN_TYPES = {"prediction", "optimization", "manual"}


def delay_risk_level_from_probability(probability: float) -> str:
    if probability >= 0.70:
        return "high"
    if probability >= 0.40:
        return "medium"
    return "low"


def calculate_route_cost(predicted_eta: float, delay_probability: float, delay_penalty: float = 0.30) -> float:
    return round(float(predicted_eta) * (1 + float(delay_probability) * delay_penalty), 2)


def generate_route_code() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"ROUTE-{stamp}-{uuid4().hex[:6].upper()}"


def generate_order_code() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"ORD-{stamp}-{uuid4().hex[:6].upper()}"


def normalize_priority(priority: str | None) -> str:
    value = (priority or "medium").strip().lower()
    if value not in DELIVERY_PRIORITIES:
        return "medium"
    return value


def priority_penalty(priority: str | None) -> float:
    value = normalize_priority(priority)
    if value == "urgent":
        return -0.10
    if value == "high":
        return -0.05
    if value == "low":
        return 0.05
    return 0.0


def format_optimized_stop_order(points: list[dict], route_order: list[int]) -> list[dict]:
    formatted: list[dict] = []
    for sequence, point_index in enumerate(route_order):
        point = points[point_index]
        formatted.append(
            {
                "sequence": sequence,
                "point_index": point_index,
                "type": point.get("type", "stop"),
                "order_code": point.get("order_code"),
                "latitude": point["latitude"],
                "longitude": point["longitude"],
                "zone_id": point.get("zone_id"),
                "priority": point.get("priority"),
            }
        )
    return formatted
