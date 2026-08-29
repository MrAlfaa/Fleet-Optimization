import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.middleware.auth_middleware import require_roles


def request_for(path: str, method: str = "GET") -> Request:
    return Request({"type": "http", "path": path, "method": method, "headers": []})


@pytest.mark.asyncio
async def test_explicit_permission_can_authorize_outside_role_template() -> None:
    dependency = require_roles(["admin", "fleet_manager", "route_planner"])
    user = {"role": "maintenance_manager", "permissions": ["routes.dispatch"]}

    result = await dependency(request_for("/api/routes/route-1/dispatch", "POST"), user)

    assert result is user


@pytest.mark.asyncio
async def test_mapped_request_requires_assigned_permission_even_when_role_was_allowed() -> None:
    dependency = require_roles(["admin", "fleet_manager", "route_planner"])
    user = {"role": "route_planner", "permissions": ["routes.view"]}

    with pytest.raises(HTTPException) as exc:
        await dependency(request_for("/api/routes/route-1/dispatch", "POST"), user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Permission required: routes.dispatch"


@pytest.mark.asyncio
async def test_admin_can_access_mapped_endpoint_with_stale_permission_snapshot() -> None:
    dependency = require_roles(["admin", "fleet_manager", "maintenance_manager"])
    user = {"role": "admin", "permissions": []}

    result = await dependency(request_for("/api/maintenance/history"), user)

    assert result is user


@pytest.mark.asyncio
async def test_unmapped_driver_endpoint_keeps_identity_role_check() -> None:
    dependency = require_roles(["driver"])
    user = {"role": "fleet_manager", "permissions": []}

    with pytest.raises(HTTPException) as exc:
        await dependency(request_for("/api/driver-device/status"), user)

    assert exc.value.status_code == 403
