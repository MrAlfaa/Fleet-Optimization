from __future__ import annotations

import asyncio
import json
import time
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_CACHE_TTL_SECONDS = 900
_weather_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def map_wmo_weather(code: int | None, wind_speed_kmh: float | None = None) -> str:
    if float(wind_speed_kmh or 0) >= 45:
        return "Windy"
    code = int(code or 0)
    if code in {45, 48}:
        return "Fog"
    if code >= 65 or code in {95, 96, 99}:
        return "Stormy"
    if code == 0:
        return "Sunny"
    return "Cloudy"


def sri_lanka_holiday(value: date) -> tuple[bool, str | None]:
    try:
        import holidays

        calendar = holidays.country_holidays("LK", years=[value.year], language="en_US")
        name = calendar.get(value)
        return name is not None, str(name) if name else None
    except ImportError:
        # Independence Day remains a safe minimal fallback when optional packages are absent.
        return (True, "Independence Day") if (value.month, value.day) == (2, 4) else (False, None)


def _fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=4) as response:  # nosec B310 - fixed HTTPS provider
        return json.loads(response.read().decode("utf-8"))


async def get_weather_context(latitude: float, longitude: float, when: datetime | None = None) -> dict[str, Any]:
    when = when or datetime.now(timezone.utc)
    cache_key = f"{latitude:.2f}:{longitude:.2f}:{when.strftime('%Y-%m-%dT%H')}"
    cached = _weather_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    params = urlencode(
        {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "current": "weather_code,precipitation,rain,wind_speed_10m",
            "hourly": "precipitation_probability",
            "timezone": "Asia/Colombo",
            "forecast_days": 2,
        }
    )
    try:
        payload = await asyncio.wait_for(asyncio.to_thread(_fetch_json, f"{OPEN_METEO_URL}?{params}"), timeout=5)
        current = payload.get("current") or {}
        probabilities = (payload.get("hourly") or {}).get("precipitation_probability") or []
        probability = float(probabilities[0]) if probabilities else None
        context = {
            "available": True,
            "source": "open_meteo",
            "weather_code": current.get("weather_code"),
            "weather_label": map_wmo_weather(current.get("weather_code"), current.get("wind_speed_10m")),
            "rain_probability": probability,
            "rain_mm": float(current.get("rain") or current.get("precipitation") or 0),
            "wind_speed_kmh": float(current.get("wind_speed_10m") or 0),
            "warning": "Storm or heavy-rain conditions may increase ETA and delay risk." if map_wmo_weather(current.get("weather_code"), current.get("wind_speed_10m")) == "Stormy" else None,
        }
        _weather_cache[cache_key] = (time.monotonic(), context)
        return context
    except Exception:
        return {
            "available": False,
            "source": "open_meteo",
            "weather_label": "Cloudy",
            "rain_probability": None,
            "warning": "Live weather is unavailable; route cost uses the trained-model default.",
        }


async def get_operational_context(value: date | None = None) -> dict[str, Any]:
    value = value or datetime.now(timezone.utc).date()
    is_holiday, holiday_name = sri_lanka_holiday(value)
    weather = await get_weather_context(6.9271, 79.8612)
    return {
        "date": value.isoformat(),
        "is_holiday": is_holiday,
        "holiday_name": holiday_name,
        "rain_probability": weather.get("rain_probability"),
        "weather_label": weather.get("weather_label", "Unavailable"),
        "artifact_source": "Olist-derived demand artifact",
        "last_refresh_at": None,
        "weather_available": weather.get("available", False),
    }
