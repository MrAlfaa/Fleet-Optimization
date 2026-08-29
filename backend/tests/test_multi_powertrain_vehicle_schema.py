import pytest

from app.models.vehicle_model import FUEL_TYPES, VEHICLE_CATEGORIES, VEHICLE_TYPES
from app.schemas.vehicle_schema import VehicleCreate


@pytest.mark.parametrize("fuel_type", sorted(FUEL_TYPES))
@pytest.mark.parametrize("category", sorted(VEHICLE_CATEGORIES))
def test_vehicle_create_accepts_every_powertrain_category_combination(fuel_type: str, category: str) -> None:
    vehicle_type = f"{fuel_type}_{category}"
    payload = VehicleCreate(
        vehicle_code=f"{fuel_type[:2]}-{category}", registration_number=f"WP {fuel_type[:1]}-{category}",
        vehicle_type=vehicle_type, vehicle_category=category, brand="Test", model="Fleet",
        year=2025, fuel_type=fuel_type,
    )
    assert vehicle_type in VEHICLE_TYPES
    assert payload.vehicle_type == vehicle_type
