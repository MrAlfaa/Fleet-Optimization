from __future__ import annotations

from math import isfinite
from typing import Any


PERIOD_WINDOWS = {
    "first_half": ("08:00", "12:00"),
    "second_half": ("13:00", "17:00"),
}

OPTIMIZER_PRIORITY = {
    "low": "standard",
    "medium": "next_day",
    "high": "express",
    "urgent": "same_day",
}

PARCEL_PROFILE_DEFAULTS: dict[str, Any] = {
    "fragile": False,
    "stackable": True,
    "max_stack_weight_kg": 0.0,
    "loading_orientation_fixed": False,
    "hazardous": False,
    "hazmat_class": None,
    "requires_refrigeration": False,
    "temp_min_celsius": None,
    "temp_max_celsius": None,
    "two_person_lift": False,
    "do_not_tilt": False,
    "service_type": "door_to_door",
}


def _positive_number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) and parsed > 0 else None


def calculated_volume_m3(length_cm: float, width_cm: float, height_cm: float) -> float:
    return round((float(length_cm) * float(width_cm) * float(height_cm)) / 1_000_000, 8)


def prepare_parcel_load_profile(data: dict[str, Any], *, delivery_period: str) -> dict[str, Any]:
    raw_profile = data.get("load_profile") or {}
    if hasattr(raw_profile, "model_dump"):
        raw_profile = raw_profile.model_dump()
    profile = {**PARCEL_PROFILE_DEFAULTS, **dict(raw_profile)}
    flags: list[str] = []
    reasons: list[str] = []

    length = _positive_number(profile.get("length_cm"))
    width = _positive_number(profile.get("width_cm"))
    height = _positive_number(profile.get("height_cm"))
    volume = _positive_number(profile.get("volume_m3")) or _positive_number(data.get("parcel_volume"))
    dimensions_imputed = False

    if length and width and height:
        volume = calculated_volume_m3(length, width, height)
    elif volume:
        side = round((volume * 1_000_000) ** (1 / 3), 4)
        length = width = height = side
        dimensions_imputed = True
        flags.append("dimensions_imputed")
    else:
        reasons.append("parcel_dimensions_and_volume_missing")

    if _positive_number(data.get("parcel_weight")) is None:
        reasons.append("parcel_weight_missing")

    start, end = PERIOD_WINDOWS.get(delivery_period, (None, None))
    if start is None:
        reasons.append("delivery_period_invalid")

    profile.update({
        "length_cm": length,
        "width_cm": width,
        "height_cm": height,
        "volume_m3": volume,
        "dimensions_imputed": dimensions_imputed,
        "optimizer_priority": OPTIMIZER_PRIORITY.get(str(data.get("priority") or "medium").lower(), "next_day"),
        "time_window_start": start,
        "time_window_end": end,
        "optimization_eligible": not reasons,
        "eligibility_reasons": reasons,
        "data_quality_flags": flags,
    })
    return profile
