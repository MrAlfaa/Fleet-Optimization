from datetime import date

from app.services.operational_context_service import map_wmo_weather, sri_lanka_holiday


def test_maps_wmo_conditions_to_route_model_categories():
    assert map_wmo_weather(0, wind_speed_kmh=5) == "Sunny"
    assert map_wmo_weather(3, wind_speed_kmh=5) == "Cloudy"
    assert map_wmo_weather(45, wind_speed_kmh=5) == "Fog"
    assert map_wmo_weather(65, wind_speed_kmh=5) == "Stormy"
    assert map_wmo_weather(1, wind_speed_kmh=55) == "Windy"


def test_detects_sri_lanka_public_holiday():
    result = sri_lanka_holiday(date(2026, 2, 4))
    assert result[0] is True
    assert result[1]

