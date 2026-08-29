from __future__ import annotations

from datetime import datetime
from typing import Any


PRIORITY_MAP = {
    "standard": "medium",
    "next_day": "medium",
    "priority": "high",
    "express": "high",
    "same_day": "urgent",
}


def _bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _optional_float(value: Any) -> float | None:
    text = str(value or "").strip()
    return float(text) if text else None


def project_member_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    start = datetime.strptime(str(row["time_window_start"]), "%H:%M").time()
    delivery_period = "first_half" if start.hour < 13 else "second_half"
    hazardous = _bool(row.get("hazardous"))
    refrigerated = _bool(row.get("requires_refrigeration"))
    return {
        "order_code": str(row["parcel_id"]).strip(),
        "drop_latitude": float(row["latitude"]),
        "drop_longitude": float(row["longitude"]),
        "parcel_weight": float(row["weight_kg"]),
        "parcel_volume": float(row["volume_m3"]),
        "priority": PRIORITY_MAP.get(str(row.get("priority_level") or "").strip().lower(), "medium"),
        "delivery_status": "pending",
        "delivery_date": str(row["delivery_date"]),
        "delivery_period": delivery_period,
        "load_profile": {
            "length_cm": float(row["length_cm"]),
            "width_cm": float(row["width_cm"]),
            "height_cm": float(row["height_cm"]),
            "volume_m3": float(row["volume_m3"]),
            "fragile": _bool(row.get("fragile")),
            "stackable": _bool(row.get("stackable")),
            "max_stack_weight_kg": float(row.get("max_stack_weight_kg") or 0),
            "loading_orientation_fixed": _bool(row.get("loading_orientation_fixed")),
            "hazardous": hazardous,
            "hazmat_class": str(row.get("hazmat_class") or "").strip() or None,
            "requires_refrigeration": refrigerated,
            "temp_min_celsius": _optional_float(row.get("temp_min_celsius")),
            "temp_max_celsius": _optional_float(row.get("temp_max_celsius")),
            "two_person_lift": _bool(row.get("two_person_lift")),
            "do_not_tilt": _bool(row.get("do_not_tilt")),
            "service_type": str(row.get("service_type") or "door_to_door").strip().lower(),
        },
    }
