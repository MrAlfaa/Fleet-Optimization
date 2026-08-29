import pytest

from app.models.route_model import build_route_plan_document
from app.schemas.route_schema import RouteOptimizationRequest
from app.services.route_set_service import (
    approved_load_delivery_ids,
    validate_route_set_for_approval,
    validate_route_set_for_dispatch,
)


def test_route_generation_does_not_require_driver_before_route_approval():
    payload = RouteOptimizationRequest(
        vehicle_id="vehicle-1",
        delivery_stops=[{"drop_latitude": 6.91, "drop_longitude": 79.87}],
    )

    assert payload.driver_id is None


def test_route_document_preserves_load_and_route_set_traceability():
    document = build_route_plan_document({
        "vehicle_id": "vehicle-1",
        "driver_id": None,
        "depot_latitude": 6.9271,
        "depot_longitude": 79.8612,
        "load_plan_id": "plan-1",
        "option_id": "balanced",
        "load_id": "load-1",
        "consolidation_id": "PCID202608291H001",
        "route_set_id": "RSET-20260829-ABC123",
    })

    assert document["route_set_id"] == "RSET-20260829-ABC123"
    assert document["consolidation_id"] == "PCID202608291H001"
    assert document["load_plan_id"] == "plan-1"
    assert document["option_id"] == "balanced"
    assert document["load_id"] == "load-1"


def test_route_set_approval_requires_one_optimized_route_per_planned_load():
    route_set = {"status": "review_required", "route_ids": ["route-1", "route-2"], "expected_route_count": 2}
    routes = [
        {"id": "route-1", "status": "optimized"},
        {"id": "route-2", "status": "optimized"},
    ]

    validate_route_set_for_approval(route_set, routes)
    with pytest.raises(ValueError, match="every approved load"):
        validate_route_set_for_approval(route_set, routes[:1])


def test_route_set_dispatch_requires_approval_and_a_driver_for_every_route():
    route_set = {"status": "approved", "route_ids": ["route-1", "route-2"], "expected_route_count": 2}
    routes = [
        {"id": "route-1", "status": "approved", "vehicle_id": "vehicle-1", "driver_id": "driver-1"},
        {"id": "route-2", "status": "approved", "vehicle_id": "vehicle-2", "driver_id": "driver-2"},
    ]

    validate_route_set_for_dispatch(route_set, routes)
    routes[1]["driver_id"] = None
    with pytest.raises(ValueError, match="driver"):
        validate_route_set_for_dispatch(route_set, routes)


def test_route_set_dispatch_rejects_one_driver_assigned_to_multiple_routes():
    route_set = {"status": "approved", "route_ids": ["route-1", "route-2"], "expected_route_count": 2}
    routes = [
        {"id": "route-1", "status": "approved", "vehicle_id": "vehicle-1", "driver_id": "driver-1"},
        {"id": "route-2", "status": "approved", "vehicle_id": "vehicle-2", "driver_id": "driver-1"},
    ]

    with pytest.raises(ValueError, match="one route"):
        validate_route_set_for_dispatch(route_set, routes)


def test_approved_load_delivery_ids_exclude_exceptions_and_reject_duplicates():
    selected = {
        "loads": [
            {"load_id": "load-1", "parcel_ids": ["parcel-1", "parcel-2"]},
            {"load_id": "load-2", "parcel_ids": ["parcel-3"]},
        ],
        "exceptions": [{"parcel_id": "parcel-4", "reasons": ["capacity"]}],
    }

    assert approved_load_delivery_ids(selected) == {
        "load-1": ["parcel-1", "parcel-2"],
        "load-2": ["parcel-3"],
    }

    selected["loads"][1]["parcel_ids"] = ["parcel-2"]
    with pytest.raises(ValueError, match="more than one approved load"):
        approved_load_delivery_ids(selected)

    selected["loads"][1]["parcel_ids"] = ["parcel-4"]
    with pytest.raises(ValueError, match="exception parcel"):
        approved_load_delivery_ids(selected)
