from app.load_optimization.engine import consolidate_batch, optimize_batch
from app.services.load_optimization_service import DEFAULT_VEHICLE_TYPE_CATALOG


def parcel(parcel_id: str, *, latitude=6.9271, longitude=79.8612, **profile_overrides):
    profile = {
        "length_cm": 50.0,
        "width_cm": 40.0,
        "height_cm": 30.0,
        "volume_m3": 0.06,
        "fragile": False,
        "stackable": True,
        "max_stack_weight_kg": 100.0,
        "loading_orientation_fixed": False,
        "do_not_tilt": False,
        "two_person_lift": False,
        "hazardous": False,
        "requires_refrigeration": False,
    }
    profile.update(profile_overrides)
    return {
        "id": parcel_id,
        "parcel_weight": 12.0,
        "drop_latitude": latitude,
        "drop_longitude": longitude,
        "priority": "medium",
        "load_profile": profile,
    }


def test_optimizer_is_deterministic_for_same_seed_and_inputs():
    rows = [parcel(f"p-{index}", latitude=6.92 + index * 0.001, longitude=79.86 + index * 0.001) for index in range(12)]

    first = optimize_batch(rows, list(DEFAULT_VEHICLE_TYPE_CATALOG), seed=31)
    second = optimize_batch(list(reversed(rows)), list(DEFAULT_VEHICLE_TYPE_CATALOG), seed=31)

    assert first == second
    assert first["selected_option"]["loads"]


def test_consolidation_exposes_regions_without_creating_virtual_loads():
    rows = [parcel(f"p-{index}", latitude=6.92 + index * 0.001, longitude=79.86 + index * 0.001) for index in range(12)]

    result = consolidate_batch(rows)

    assert result["parcel_count"] == 12
    assert result["cluster_method"] in {"hdbscan", "single_region", "single_region_fallback"}
    assert sum(region["parcel_count"] for region in result["regions"]) == 12
    assert {parcel_id for region in result["regions"] for parcel_id in region["parcel_ids"]} == {
        row["id"] for row in rows
    }
    assert "pareto_options" not in result


def test_special_loads_only_use_compatible_virtual_vehicle_types():
    rows = [
        parcel("cold", requires_refrigeration=True, temp_min_celsius=2, temp_max_celsius=8),
        parcel("hazard", hazardous=True, hazmat_class="3"),
    ]

    result = optimize_batch(rows, list(DEFAULT_VEHICLE_TYPE_CATALOG), seed=17)
    catalog = {item["code"]: item for item in DEFAULT_VEHICLE_TYPE_CATALOG}
    assigned = {
        parcel_id: catalog[load["vehicle_type_code"]]
        for load in result["selected_option"]["loads"]
        for parcel_id in load["parcel_ids"]
    }

    assert assigned["cold"]["is_refrigerated"] is True
    assert assigned["hazard"]["is_hazmat_certified"] is True


def test_infeasible_parcel_is_reported_and_never_silently_assigned():
    oversized = parcel("oversized", length_cm=1_200, width_cm=400, height_cm=400, volume_m3=192)

    result = optimize_batch([oversized], list(DEFAULT_VEHICLE_TYPE_CATALOG), seed=17)

    assert result["selected_option"]["loads"] == []
    assert result["exceptions"][0]["parcel_id"] == "oversized"
    assert "dimension" in " ".join(result["exceptions"][0]["reasons"]).lower()


def test_placements_remain_inside_cargo_bay_and_do_not_overlap():
    rows = [parcel(f"p-{index}") for index in range(8)]
    result = optimize_batch(rows, list(DEFAULT_VEHICLE_TYPE_CATALOG), seed=17)
    catalog = {item["code"]: item for item in DEFAULT_VEHICLE_TYPE_CATALOG}

    for load in result["selected_option"]["loads"]:
        vehicle = catalog[load["vehicle_type_code"]]
        placements = load["placements"]
        for item in placements:
            assert item["x_cm"] + item["length_cm"] <= vehicle["cargo_length_cm"] + 1e-9
            assert item["y_cm"] + item["width_cm"] <= vehicle["cargo_width_cm"] + 1e-9
            assert item["z_cm"] + item["height_cm"] <= vehicle["cargo_height_cm"] + 1e-9
        for index, first in enumerate(placements):
            for second in placements[index + 1:]:
                separated = (
                    first["x_cm"] + first["length_cm"] <= second["x_cm"]
                    or second["x_cm"] + second["length_cm"] <= first["x_cm"]
                    or first["y_cm"] + first["width_cm"] <= second["y_cm"]
                    or second["y_cm"] + second["width_cm"] <= first["y_cm"]
                    or first["z_cm"] + first["height_cm"] <= second["z_cm"]
                    or second["z_cm"] + second["height_cm"] <= first["z_cm"]
                )
                assert separated


def test_fragile_parcel_is_placed_above_a_stackable_support_parcel():
    support = parcel(
        "support",
        length_cm=60,
        width_cm=40,
        height_cm=30,
        volume_m3=0.072,
        fragile=False,
        stackable=True,
        max_stack_weight_kg=50,
    )
    fragile = parcel(
        "fragile",
        length_cm=40,
        width_cm=30,
        height_cm=20,
        volume_m3=0.024,
        fragile=True,
        stackable=False,
    )

    result = optimize_batch([fragile, support], list(DEFAULT_VEHICLE_TYPE_CATALOG), seed=17)
    placements = {
        item["parcel_id"]: item
        for load in result["selected_option"]["loads"]
        for item in load["placements"]
    }

    assert placements["support"]["z_cm"] == 0
    assert placements["fragile"]["z_cm"] >= placements["support"]["height_cm"]
    assert placements["fragile"]["layer"] > placements["support"]["layer"]


def test_each_candidate_load_has_a_branch_return_route_preview():
    rows = [parcel(f"p-{index}", latitude=6.91 + index * 0.002, longitude=79.85 + index * 0.002) for index in range(6)]

    result = optimize_batch(rows, list(DEFAULT_VEHICLE_TYPE_CATALOG), seed=17)

    assert len(result["pareto_options"]) >= 3
    for option in result["pareto_options"][:3]:
        assert option["objectives"]["estimated_route_km"] > 0
        assert isinstance(option["exceptions"], list)
        for load in option["loads"]:
            assert load["route_preview"][0]["type"] == "branch"
            assert load["route_preview"][-1]["type"] == "branch"
            assert {point["parcel_id"] for point in load["route_preview"] if point["type"] == "parcel"} == set(load["parcel_ids"])
