from app.utils.demand_utils import estimate_required_vehicles, normalize_demand_level
from app.utils.sri_lanka_zones import (
    enrich_zone_record,
    operational_zone_id,
    operational_zone_options,
    source_zone_id,
)


def test_demand_levels_follow_approved_model_policy() -> None:
    assert normalize_demand_level(12) == "low"
    assert normalize_demand_level(12.01) == "medium"
    assert normalize_demand_level(18) == "medium"
    assert normalize_demand_level(18.01) == "high"
    assert normalize_demand_level(25) == "high"
    assert normalize_demand_level(25.01) == "very_high"


def test_required_vehicles_follow_twelve_orders_per_vehicle_policy() -> None:
    assert estimate_required_vehicles(0) == 1
    assert estimate_required_vehicles(12) == 1
    assert estimate_required_vehicles(12.01) == 2
    assert estimate_required_vehicles(24) == 2


def test_current_operational_catalog_contains_fifteen_direct_colombo_zones() -> None:
    options = operational_zone_options()

    assert len(options) == 15
    assert len({item["operational_zone_id"] for item in options}) == 15
    assert all(item["operational_zone_id"].startswith("LK_") for item in options)
    assert all(item["source_zone_id"] == item["operational_zone_id"] for item in options)
    assert {item["operational_zone_id"] for item in options} >= {
        "LK_colombo_central",
        "LK_kollupitiya",
        "LK_borella",
        "LK_wattala",
        "LK_piliyandala",
    }


def test_legacy_source_ids_are_normalized_but_never_exposed() -> None:
    assert operational_zone_id("SP_sao_paulo") == "LK_colombo_central"
    assert source_zone_id("LK_colombo_central") == "LK_colombo_central"

    enriched = enrich_zone_record({"zone_id": "SP_sao_paulo", "predicted_demand": 14})

    assert enriched["zone_id"] == "LK_colombo_central"
    assert enriched["source_zone_id"] == "LK_colombo_central"
    assert "SP_" not in str(enriched)
