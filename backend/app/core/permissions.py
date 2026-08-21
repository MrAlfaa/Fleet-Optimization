from typing import Any


PERMISSION_GROUPS: dict[str, tuple[str, ...]] = {
    "Workspace": ("dashboard.view", "alerts.view", "reports.view", "reports.export"),
    "Fleet": ("vehicles.view", "vehicles.create", "vehicles.update", "maintenance.view", "maintenance.manage"),
    "Intelligence": ("predictive.view", "predictive.run", "demand.view", "demand.refresh", "readiness.view"),
    "Operations": (
        "deliveries.view",
        "deliveries.manage",
        "routes.view",
        "routes.optimize",
        "routes.dispatch",
        "live_trips.view",
    ),
    "Administration": ("drivers.manage", "users.manage", "permissions.manage"),
}

ALL_PERMISSIONS = frozenset(permission for values in PERMISSION_GROUPS.values() for permission in values)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": ALL_PERMISSIONS,
    "fleet_manager": frozenset(
        permission for permission in ALL_PERMISSIONS if permission not in {"users.manage", "permissions.manage"}
    ),
    "maintenance_manager": frozenset(
        {
            "dashboard.view", "alerts.view", "reports.view", "reports.export", "vehicles.view", "maintenance.view",
            "maintenance.manage", "predictive.view", "predictive.run", "readiness.view",
        }
    ),
    "route_planner": frozenset(
        {
            "dashboard.view", "alerts.view", "reports.view", "reports.export", "vehicles.view", "demand.view", "demand.refresh",
            "readiness.view", "deliveries.view", "deliveries.manage", "routes.view", "routes.optimize",
            "routes.dispatch", "live_trips.view",
        }
    ),
    "driver": frozenset(),
}


def permissions_for_role(role: str) -> set[str]:
    return set(ROLE_PERMISSIONS.get(role, frozenset()))


def effective_permissions(role: str, overrides: dict[str, Any] | None = None) -> set[str]:
    maximum = permissions_for_role(role)
    if role == "admin":
        return maximum
    denied = set((overrides or {}).get("deny", []))
    return maximum - denied


def validate_permission_selection(role: str, permissions: list[str]) -> set[str]:
    return set(permissions) & permissions_for_role(role)


def permission_overrides_from_selection(role: str, permissions: list[str]) -> dict[str, list[str]]:
    maximum = permissions_for_role(role)
    selected = validate_permission_selection(role, permissions)
    return {"deny": sorted(maximum - selected)}


def permission_catalog() -> dict[str, Any]:
    return {
        "groups": {group: list(values) for group, values in PERMISSION_GROUPS.items()},
        "role_permissions": {role: sorted(values) for role, values in ROLE_PERMISSIONS.items()},
    }


def permission_for_request(path: str, method: str) -> str | None:
    method = method.upper()
    if path.startswith("/api/dashboard"):
        return "dashboard.view"
    if path.startswith("/api/vehicles"):
        return "vehicles.view" if method == "GET" else ("vehicles.create" if method == "POST" else "vehicles.update")
    if path.startswith("/api/maintenance"):
        return "maintenance.view" if method == "GET" else "maintenance.manage"
    if path.startswith("/api/predictive-maintenance"):
        return "predictive.view" if method == "GET" else "predictive.run"
    if path.startswith("/api/demand"):
        return "demand.view" if method == "GET" else "demand.refresh"
    if path.startswith("/api/deliveries"):
        return "deliveries.view" if method == "GET" else "deliveries.manage"
    if path.startswith("/api/routes"):
        if method == "GET":
            return "routes.view"
        return "routes.dispatch" if path.endswith("/dispatch") else "routes.optimize"
    if path.startswith("/api/live-trips"):
        return "live_trips.view"
    if path.startswith("/api/alerts"):
        return "alerts.view"
    if path.startswith("/api/intelligence"):
        return "readiness.view"
    if path.startswith("/api/reports"):
        return "reports.export" if method == "GET" else "reports.view"
    return None
