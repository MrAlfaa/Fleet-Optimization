import asyncio

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.routes.route_routes import require_route_geometry_user
from app.services.route_geometry_service import (
    RouteGeometryService,
    ensure_route_geometry_access,
    route_plan_coordinates,
)


COORDINATES = [(6.9271, 79.8612), (6.8649, 79.8997)]


def test_osrm_geometry_is_cached_by_ordered_coordinate_hash() -> None:
    calls = 0

    async def fetcher(url: str, timeout: float) -> dict:
        nonlocal calls
        calls += 1
        assert "79.861200,6.927100;79.899700,6.864900" in url
        assert timeout == 5.0
        return {
            "code": "Ok",
            "routes": [{"geometry": {"type": "LineString", "coordinates": [[79.8612, 6.9271], [79.88, 6.90], [79.8997, 6.8649]]}}],
        }

    service = RouteGeometryService(fetcher=fetcher, now=lambda: 100.0, sleep=lambda _: asyncio.sleep(0))
    first = asyncio.run(service.geometry(COORDINATES))
    second = asyncio.run(service.geometry(COORDINATES))

    assert first["geometry_source"] == "osrm"
    assert first["coordinates"][1] == {"latitude": 6.9, "longitude": 79.88}
    assert second["coordinates"] == first["coordinates"]
    assert second["geometry_source"] == "osrm"
    assert second["cached"] is True
    assert calls == 1


def test_osrm_malformed_response_falls_back_to_straight_line() -> None:
    async def fetcher(_: str, __: float) -> dict:
        return {"code": "NoRoute", "routes": []}

    service = RouteGeometryService(fetcher=fetcher, now=lambda: 100.0, sleep=lambda _: asyncio.sleep(0))
    result = asyncio.run(service.geometry(COORDINATES))

    assert result == {
        "geometry_source": "fallback",
        "coordinates": [
            {"latitude": 6.9271, "longitude": 79.8612},
            {"latitude": 6.8649, "longitude": 79.8997},
        ],
        "cached": False,
    }


def test_osrm_timeout_falls_back_without_raising() -> None:
    async def fetcher(_: str, __: float) -> dict:
        raise TimeoutError("weathered network")

    service = RouteGeometryService(fetcher=fetcher, now=lambda: 100.0, sleep=lambda _: asyncio.sleep(0))
    result = asyncio.run(service.geometry(COORDINATES))

    assert result["geometry_source"] == "fallback"


def test_geometry_requires_at_least_two_valid_coordinates() -> None:
    service = RouteGeometryService(now=lambda: 100.0, sleep=lambda _: asyncio.sleep(0))

    try:
        asyncio.run(service.geometry([(6.9271, 79.8612)]))
    except ValueError as exc:
        assert "at least two" in str(exc)
    else:
        raise AssertionError("Expected a coordinate validation error")


def test_route_plan_coordinates_preserve_optimized_stop_order() -> None:
    coordinates = route_plan_coordinates({
        "depot_latitude": 6.9271,
        "depot_longitude": 79.8612,
        "optimized_stop_order": [
            {"latitude": 6.88, "longitude": 79.90},
            {"drop_latitude": 6.86, "drop_longitude": 79.92},
        ],
    })

    assert coordinates == [
        (6.9271, 79.8612),
        (6.88, 79.90),
        (6.86, 79.92),
        (6.9271, 79.8612),
    ]


def test_driver_can_only_view_geometry_for_assigned_route() -> None:
    driver_id = ObjectId()
    ensure_route_geometry_access({"driver_id": driver_id}, {"id": str(driver_id), "role": "driver"})

    with pytest.raises(PermissionError, match="assigned"):
        ensure_route_geometry_access(
            {"driver_id": ObjectId()},
            {"id": str(driver_id), "role": "driver"},
        )


def test_planning_role_can_view_route_geometry() -> None:
    ensure_route_geometry_access({"driver_id": ObjectId()}, {"id": str(ObjectId()), "role": "route_planner"})


@pytest.mark.asyncio
async def test_driver_geometry_dependency_bypasses_fleet_permission_only_for_driver() -> None:
    driver = {"id": str(ObjectId()), "role": "driver", "permissions": []}
    assert await require_route_geometry_user(driver) == driver

    stale_admin = {"id": str(ObjectId()), "role": "admin", "permissions": []}
    assert await require_route_geometry_user(stale_admin) == stale_admin

    with pytest.raises(HTTPException) as exc:
        await require_route_geometry_user({"id": str(ObjectId()), "role": "route_planner", "permissions": []})
    assert exc.value.status_code == 403
