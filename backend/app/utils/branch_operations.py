from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from app.core.config import settings


FIRST_HALF = "first_half"
SECOND_HALF = "second_half"
DELIVERY_PERIODS = {FIRST_HALF, SECOND_HALF}
COLOMBO_TIMEZONE = ZoneInfo("Asia/Colombo")

_PERIOD_WINDOWS = {
    FIRST_HALF: (time(8, 0), time(12, 0)),
    SECOND_HALF: (time(13, 0), time(17, 0)),
}


def get_branch_profile() -> dict[str, Any]:
    return {
        "id": "colombo_central_branch",
        "name": settings.branch_name,
        "address": settings.branch_address,
        "latitude": float(settings.branch_latitude),
        "longitude": float(settings.branch_longitude),
        "timezone": "Asia/Colombo",
        "delivery_periods": [
            {"id": FIRST_HALF, "label": "First Half", "start": "08:00", "end": "12:00"},
            {"id": SECOND_HALF, "label": "Second Half", "start": "13:00", "end": "17:00"},
        ],
    }


def apply_branch_origin(data: dict[str, Any]) -> dict[str, Any]:
    branch = get_branch_profile()
    return {
        **data,
        "pickup_latitude": branch["latitude"],
        "pickup_longitude": branch["longitude"],
        "pickup_address": branch["address"],
        "pickup_source": "colombo_branch",
    }


def apply_route_branch(data: dict[str, Any]) -> dict[str, Any]:
    branch = get_branch_profile()
    return {
        **data,
        "depot_latitude": branch["latitude"],
        "depot_longitude": branch["longitude"],
        "depot_name": branch["name"],
    }


def build_delivery_schedule(delivery_date: date, delivery_period: str) -> dict[str, Any]:
    if delivery_period not in DELIVERY_PERIODS:
        raise ValueError("Delivery period must be first_half or second_half")
    start_time, end_time = _PERIOD_WINDOWS[delivery_period]
    return {
        "delivery_date": delivery_date.isoformat(),
        "delivery_period": delivery_period,
        "delivery_window_start": datetime.combine(delivery_date, start_time, tzinfo=COLOMBO_TIMEZONE),
        "delivery_window_end": datetime.combine(delivery_date, end_time, tzinfo=COLOMBO_TIMEZONE),
        "scheduled_date": datetime.combine(delivery_date, start_time, tzinfo=COLOMBO_TIMEZONE),
    }


def delivery_batch_key(order: dict[str, Any]) -> tuple[str, str] | None:
    delivery_date = order.get("delivery_date")
    delivery_period = order.get("delivery_period")
    if delivery_date and delivery_period in DELIVERY_PERIODS:
        date_value = delivery_date.isoformat() if isinstance(delivery_date, date) else str(delivery_date)[:10]
        return date_value, str(delivery_period)

    scheduled = order.get("scheduled_date")
    if not isinstance(scheduled, datetime):
        return None
    local = scheduled if scheduled.tzinfo else scheduled.replace(tzinfo=COLOMBO_TIMEZONE)
    local = local.astimezone(COLOMBO_TIMEZONE)
    inferred_period = FIRST_HALF if local.hour < 13 else SECOND_HALF
    return local.date().isoformat(), inferred_period
