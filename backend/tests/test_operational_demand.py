import pytest
from app.utils.sri_lanka_zones import nearest_operational_zone, prepare_delivery_zone


def test_nearest_zone_maps_colombo_coordinates():
    result = nearest_operational_zone(6.9271, 79.8612)
    assert result["operational_zone_id"] == "LK_colombo_central"
    assert result["source_zone_id"] == "LK_colombo_central"
    assert result["within_service_area"] is True


def test_confirmed_operational_zone_preserves_source_mapping():
    result = prepare_delivery_zone(6.8649, 79.8997, "LK_nugegoda", "confirmed")
    assert result["zone_id"] == "LK_nugegoda"
    assert result["source_zone_id"] == "LK_nugegoda"
    assert result["zone_assignment_method"] == "confirmed"


def test_unknown_operational_zone_is_rejected():
    with pytest.raises(ValueError, match="Unknown"):
        prepare_delivery_zone(6.9, 79.9, "LK_unknown")
