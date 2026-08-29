from copy import deepcopy

import pytest

from app.models.load_optimization_model import (
    build_batch_fingerprint,
    build_consolidation_document,
    build_consolidation_id,
    build_optimization_job_document,
    validate_plan_transition,
)
from app.services.load_optimization_service import (
    DEFAULT_VEHICLE_TYPE_CATALOG,
    assess_batch_orders,
    candidate_generation_state,
    public_readiness_summary,
    selected_parcel_load_map,
    vehicle_supports_virtual_load,
    validate_route_handoff,
    planning_change_requires_revision,
)


def order(order_id="order-a", **overrides):
    value = {
        "id": order_id,
        "delivery_status": "pending",
        "delivery_date": "2026-08-30",
        "delivery_period": "first_half",
        "parcel_weight": 12.0,
        "load_planning_status": "unplanned",
        "load_profile": {
            "optimization_eligible": True,
            "length_cm": 50,
            "width_cm": 40,
            "height_cm": 30,
            "volume_m3": 0.06,
            "hazardous": False,
            "requires_refrigeration": False,
        },
    }
    value.update(overrides)
    return value


def test_batch_fingerprint_is_deterministic_and_order_independent():
    first = build_batch_fingerprint([order("b"), order("a")], "2026-08-30", "first_half", seed=17)
    second = build_batch_fingerprint([order("a"), order("b")], "2026-08-30", "first_half", seed=17)
    changed = build_batch_fingerprint([order("a", parcel_weight=13), order("b")], "2026-08-30", "first_half", seed=17)

    assert first == second
    assert first != changed


def test_batch_assessment_separates_data_exceptions_from_lifecycle_exclusions():
    orders = [
        order("ready"),
        order("missing", load_profile={"optimization_eligible": False, "eligibility_reasons": ["parcel_weight_missing"]}),
        order("reserved", load_planning_status="reserved"),
        order("cancelled", delivery_status="cancelled"),
    ]

    result = assess_batch_orders(orders, "2026-08-30", "first_half")

    assert [item["id"] for item in result["eligible_orders"]] == ["ready"]
    assert {item["order_id"] for item in result["exceptions"]} == {"missing"}
    assert {item["order_id"] for item in result["excluded_orders"]} == {"reserved", "cancelled"}


def test_job_document_records_manual_batch_lock_and_source_fingerprint():
    orders = [order("a"), order("b")]
    document = build_optimization_job_document(
        orders=orders,
        delivery_date="2026-08-30",
        delivery_period="first_half",
        seed=17,
        created_by="user-1",
    )

    assert document["status"] == "queued"
    assert document["batch_key"] == "colombo_central_branch:2026-08-30:first_half"
    assert document["order_ids"] == ["a", "b"]
    assert len(document["input_fingerprint"]) == 64
    assert document["progress_percent"] == 0


def test_consolidation_id_is_business_readable_and_period_scoped():
    assert build_consolidation_id("2026-08-29", "first_half", 1) == "PCID202608291H001"
    assert build_consolidation_id("2026-08-29", "second_half", 27) == "PCID202608292H027"


def test_consolidation_document_locks_exact_source_and_map_points():
    orders = [
        order("b", order_code="PARCEL-B", drop_latitude=6.91, drop_longitude=79.87, zone_id="borella"),
        order("a", order_code="PARCEL-A", drop_latitude=6.92, drop_longitude=79.86, zone_id="colombo-central"),
    ]
    snapshot = {
        "cluster_method": "hdbscan",
        "regions": [{
            "region_id": 0,
            "parcel_count": 2,
            "centroid": {"latitude": 6.915, "longitude": 79.865},
            "parcel_ids": ["a", "b"],
        }],
    }

    document = build_consolidation_document(
        consolidation_id="PCID202608291H001",
        sequence=1,
        orders=orders,
        snapshot=snapshot,
        delivery_date="2026-08-29",
        delivery_period="first_half",
        source_fingerprint="a" * 64,
        created_by="user-1",
    )

    assert document["status"] == "active"
    assert document["parcel_ids"] == ["a", "b"]
    assert document["source_fingerprint"] == "a" * 64
    assert [point["parcel_id"] for point in document["parcel_points"]] == ["a", "b"]
    assert document["parcel_points"][0]["region_id"] == 0


def test_consolidated_parcels_are_eligible_for_the_locked_job_only():
    locked = order("locked", load_planning_status="consolidated", active_consolidation_id="PCID202608291H001")

    default_result = assess_batch_orders([locked], "2026-08-30", "first_half")
    locked_result = assess_batch_orders(
        [locked],
        "2026-08-30",
        "first_half",
        allowed_planning_statuses={"consolidated"},
        consolidation_id="PCID202608291H001",
    )

    assert default_result["eligible_orders"] == []
    assert [item["id"] for item in locked_result["eligible_orders"]] == ["locked"]


def test_invalid_plan_state_transition_is_rejected():
    validate_plan_transition("review_required", "approved")
    with pytest.raises(ValueError, match="Invalid load plan transition"):
        validate_plan_transition("approved", "running")


def test_catalog_uses_supported_main_fleet_categories_only():
    assert {item["category"] for item in DEFAULT_VEHICLE_TYPE_CATALOG} <= {"car", "van", "truck", "bus"}
    assert any(item["is_refrigerated"] for item in DEFAULT_VEHICLE_TYPE_CATALOG)
    assert any(item["is_hazmat_certified"] for item in DEFAULT_VEHICLE_TYPE_CATALOG)


def test_physical_vehicle_matching_enforces_readiness_capacity_and_special_capabilities():
    virtual_load = {
        "vehicle_type_code": "MEDIUM_VAN_REEFER",
        "capacity_kg": 1100,
        "capacity_m3": 6,
        "used_weight_kg": 900,
        "used_volume_m3": 5,
        "parcel_count": 40,
        "requires_refrigeration": True,
        "temp_min_celsius": 2,
        "temp_max_celsius": 8,
        "hazardous": False,
    }
    vehicle = {
        "status": "active",
        "payload_capacity_kg": 1200,
        "dispatch_hold": False,
        "load_profile": {
            "capacity_m3": 6.5,
            "cargo_length_cm": 360,
            "cargo_width_cm": 180,
            "cargo_height_cm": 180,
            "max_parcels": 60,
            "is_refrigerated": True,
            "temp_min_celsius": 0,
            "temp_max_celsius": 10,
            "is_hazmat_certified": False,
        },
    }

    assert vehicle_supports_virtual_load(vehicle, virtual_load)["eligible"] is True
    held = deepcopy(vehicle)
    held["dispatch_hold"] = True
    assert vehicle_supports_virtual_load(held, virtual_load)["eligible"] is False
    warm_only = deepcopy(vehicle)
    warm_only["load_profile"]["temp_min_celsius"] = 5
    assert "temperature" in " ".join(vehicle_supports_virtual_load(warm_only, virtual_load)["reasons"]).lower()
    short_bay = deepcopy(vehicle)
    short_bay["load_profile"]["cargo_length_cm"] = 250
    virtual_load.update({"cargo_length_cm": 320, "cargo_width_cm": 170, "cargo_height_cm": 175})
    assert "dimensions" in " ".join(vehicle_supports_virtual_load(short_bay, virtual_load)["reasons"]).lower()


def test_vehicle_suggestion_readiness_does_not_expose_internal_vehicle_document():
    summary = public_readiness_summary({
        "eligible": True,
        "blocking_reasons": [],
        "warnings": ["No recent predictive maintenance result is available"],
        "vehicle": {"_id": object()},
    })

    assert summary == {
        "eligible": True,
        "blocking_reasons": [],
        "warnings": ["No recent predictive maintenance result is available"],
    }


def test_route_handoff_requires_approved_exact_load_and_confirmed_vehicle():
    plan = {
        "plan_id": "plan-1",
        "status": "approved",
        "selected_option": {"loads": [{
            "load_id": "load-1",
            "parcel_ids": ["a", "b"],
            "assigned_vehicle_id": "vehicle-1",
        }]},
    }

    assert validate_route_handoff(plan, "load-1", "vehicle-1", ["b", "a"])["load_id"] == "load-1"
    with pytest.raises(ValueError, match="exact parcel set"):
        validate_route_handoff(plan, "load-1", "vehicle-1", ["a"])
    with pytest.raises(ValueError, match="confirmed physical vehicle"):
        validate_route_handoff(plan, "load-1", "vehicle-2", ["a", "b"])


def test_selected_candidate_rebinds_parcels_to_approved_load_ids():
    selected = {
        "loads": [
            {"load_id": "approved-load-1", "parcel_ids": ["a", "b"]},
            {"load_id": "approved-load-2", "parcel_ids": ["c"]},
        ],
        "exceptions": [{"parcel_id": "d", "reasons": ["capacity"]}],
    }

    assignments = selected_parcel_load_map(selected)

    assert assignments == {
        "a": "approved-load-1",
        "b": "approved-load-1",
        "c": "approved-load-2",
    }


def test_planning_inputs_invalidate_a_saved_plan_but_customer_notes_do_not():
    existing = order("a")

    assert planning_change_requires_revision(existing, {"parcel_weight": 14}) is True
    assert planning_change_requires_revision(existing, {"drop_latitude": 6.8}) is True
    assert planning_change_requires_revision(existing, {"delivery_period": "second_half"}) is True
    assert planning_change_requires_revision(existing, {"customer_phone": "0710000000"}) is False


@pytest.mark.parametrize(
    ("job", "plan", "expected_status", "can_generate", "can_retry"),
    [
        (None, None, "not_started", True, False),
        ({"status": "queued"}, None, "queued", False, False),
        ({"status": "running"}, None, "running", False, False),
        ({"status": "failed"}, None, "failed", True, True),
        ({"status": "cancelled"}, None, "cancelled", True, True),
        ({"status": "completed"}, {"status": "review_required"}, "ready", False, False),
        ({"status": "completed"}, {"status": "approved"}, "approved", False, False),
    ],
)
def test_candidate_generation_state_allows_only_first_generation_or_failed_retry(
    job, plan, expected_status, can_generate, can_retry,
):
    result = candidate_generation_state(job=job, plan=plan)

    assert result == {
        "status": expected_status,
        "can_generate": can_generate,
        "can_retry": can_retry,
    }
