from typing import Any


PERMISSION_GROUPS: dict[str, tuple[str, ...]] = {
    "Workspace pages": ("dashboard.view", "alerts.view", "reports.view", "readiness.view"),
    "Fleet pages": (
        "vehicles.view", "maintenance.view", "maintenance.work_orders.view",
        "maintenance.history.view", "maintenance.inspections.view",
    ),
    "Vehicle workspace tabs": (
        "vehicles.tab.overview", "vehicles.tab.risk_assessment", "vehicles.tab.maintenance",
        "vehicles.tab.parts_inspections", "vehicles.tab.activity",
    ),
    "Planning pages": (
        "predictive.view", "demand.view", "zones.view", "deliveries.view", "load_optimization.view",
        "routes.view", "live_trips.view",
    ),
    "Operational actions": (
        "vehicles.create", "vehicles.update", "maintenance.manage", "predictive.run", "demand.refresh",
        "deliveries.manage", "load_optimization.generate", "load_optimization.approve",
        "load_optimization.assign", "load_optimization.cancel", "routes.optimize", "routes.approve", "routes.dispatch", "reports.export",
    ),
    "Administration": ("drivers.manage", "users.manage", "permissions.manage"),
}

PERMISSION_METADATA: dict[str, dict[str, Any]] = {
    "dashboard.view": {"label": "Dashboard", "type": "page", "description": "Open the operational dashboard."},
    "alerts.view": {"label": "Alerts", "type": "page", "description": "Review fleet alerts."},
    "reports.view": {"label": "Reports", "type": "page", "description": "Open report workspaces and saved reports."},
    "readiness.view": {"label": "Fleet Readiness", "type": "page", "description": "Review fleet capacity and dispatch readiness."},
    "vehicles.view": {"label": "Vehicles", "type": "page", "description": "Search vehicles and open vehicle workspaces."},
    "maintenance.view": {"label": "Maintenance Command Center", "type": "page", "description": "Open the maintenance command center."},
    "maintenance.work_orders.view": {"label": "Maintenance Work", "type": "page", "description": "Review active and completed maintenance work.", "parent": "maintenance.view"},
    "maintenance.history.view": {"label": "Maintenance History", "type": "page", "description": "Review immutable maintenance history.", "parent": "maintenance.view"},
    "maintenance.inspections.view": {"label": "Vehicle Inspections", "type": "page", "description": "Open inspection queues and workspaces.", "parent": "maintenance.view"},
    "vehicles.tab.overview": {"label": "Overview", "type": "tab", "description": "View the vehicle overview tab.", "parent": "vehicles.view"},
    "vehicles.tab.risk_assessment": {"label": "Risk Assessment", "type": "tab", "description": "View vehicle risk assessments.", "parent": "vehicles.view"},
    "vehicles.tab.maintenance": {"label": "Maintenance", "type": "tab", "description": "View vehicle maintenance records.", "parent": "vehicles.view"},
    "vehicles.tab.parts_inspections": {"label": "Parts & Inspections", "type": "tab", "description": "View tracked parts and inspections.", "parent": "vehicles.view"},
    "vehicles.tab.activity": {"label": "Activity", "type": "tab", "description": "View the vehicle activity timeline.", "parent": "vehicles.view"},
    "predictive.view": {"label": "Risk Assessments", "type": "page", "description": "Review fleet risk assessments."},
    "demand.view": {"label": "Demand Forecast", "type": "page", "description": "Review approved demand forecasts."},
    "zones.view": {"label": "Zones", "type": "page", "description": "View operational zones and map coverage."},
    "deliveries.view": {"label": "Parcel Gallery", "type": "page", "description": "Review parcel delivery orders."},
    "load_optimization.view": {"label": "Load Optimization", "type": "page", "description": "Review parcel load plans and placement."},
    "routes.view": {"label": "Route Planning", "type": "page", "description": "Review route plans and assignments."},
    "live_trips.view": {"label": "Live Trips", "type": "page", "description": "Monitor dispatched trips."},
    "vehicles.create": {"label": "Create vehicles", "type": "action", "description": "Add new vehicles.", "parent": "vehicles.view"},
    "vehicles.update": {"label": "Edit vehicles", "type": "action", "description": "Edit or retire vehicles.", "parent": "vehicles.view"},
    "maintenance.manage": {"label": "Manage maintenance", "type": "action", "description": "Create and progress inspections and maintenance work.", "parent": "maintenance.view"},
    "predictive.run": {"label": "Create assessments", "type": "action", "description": "Create a new vehicle risk assessment.", "parent": "predictive.view"},
    "demand.refresh": {"label": "Generate forecasts", "type": "action", "description": "Generate and activate a demand forecast.", "parent": "demand.view"},
    "deliveries.manage": {"label": "Manage parcels", "type": "action", "description": "Create, edit, or cancel delivery orders.", "parent": "deliveries.view"},
    "load_optimization.generate": {"label": "Generate load plans", "type": "action", "description": "Reserve eligible parcels and start load optimization.", "parent": "load_optimization.view"},
    "load_optimization.approve": {"label": "Approve load plans", "type": "action", "description": "Approve a reviewed load plan revision.", "parent": "load_optimization.view"},
    "load_optimization.assign": {"label": "Assign physical vehicles", "type": "action", "description": "Confirm compatible vehicles for approved virtual loads.", "parent": "load_optimization.view"},
    "load_optimization.cancel": {"label": "Cancel load plans", "type": "action", "description": "Cancel queued jobs or release approved plans.", "parent": "load_optimization.view"},
    "routes.optimize": {"label": "Optimize routes", "type": "action", "description": "Create optimized route plans.", "parent": "routes.view"},
    "routes.approve": {"label": "Approve route sets", "type": "action", "description": "Approve a complete route set before driver assignment.", "parent": "routes.view"},
    "routes.dispatch": {"label": "Dispatch routes", "type": "action", "description": "Assign and dispatch approved routes.", "parent": "routes.view"},
    "reports.export": {"label": "Export reports", "type": "action", "description": "Download report files.", "parent": "reports.view"},
    "drivers.manage": {"label": "Driver Management", "type": "page", "description": "Provision drivers and manage registered devices."},
    "users.manage": {"label": "User Management", "type": "page", "description": "Create and manage web portal users."},
    "permissions.manage": {"label": "Access Control", "type": "action", "description": "Assign individual user access.", "parent": "users.manage"},
}

ALL_PERMISSIONS = frozenset(permission for values in PERMISSION_GROUPS.values() for permission in values)


def _with_dependencies(permissions: set[str]) -> set[str]:
    normalized = set(permissions) & ALL_PERMISSIONS
    pending = list(normalized)
    while pending:
        permission = pending.pop()
        parent = PERMISSION_METADATA.get(permission, {}).get("parent")
        if parent and parent not in normalized:
            normalized.add(parent)
            pending.append(parent)
    return normalized


BASE_VEHICLE_TABS = {
    "vehicles.tab.overview", "vehicles.tab.risk_assessment", "vehicles.tab.maintenance",
    "vehicles.tab.parts_inspections", "vehicles.tab.activity",
}
MAINTENANCE_PAGES = {
    "maintenance.work_orders.view", "maintenance.history.view", "maintenance.inspections.view",
}

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": ALL_PERMISSIONS,
    "fleet_manager": frozenset(ALL_PERMISSIONS - {"users.manage", "permissions.manage"}),
    "maintenance_manager": frozenset({
        "dashboard.view", "alerts.view", "reports.view", "reports.export", "vehicles.view", "vehicles.update",
        "maintenance.view", "maintenance.manage", "predictive.view", "predictive.run", "readiness.view",
    } | BASE_VEHICLE_TABS | MAINTENANCE_PAGES),
    "route_planner": frozenset({
        "dashboard.view", "alerts.view", "reports.view", "reports.export", "vehicles.view", "demand.view",
        "demand.refresh", "zones.view", "readiness.view", "deliveries.view", "deliveries.manage",
        "load_optimization.view", "load_optimization.generate", "load_optimization.approve",
        "load_optimization.assign", "load_optimization.cancel", "routes.view",
        "routes.optimize", "routes.approve", "routes.dispatch", "live_trips.view", "vehicles.tab.overview",
        "vehicles.tab.risk_assessment", "vehicles.tab.activity",
    }),
    "driver": frozenset(),
}


def permissions_for_role(role: str) -> set[str]:
    """Return a role's initial template, not an authorization ceiling."""
    return set(ROLE_PERMISSIONS.get(role, frozenset()))


def normalize_permission_selection(permissions: list[str] | set[str]) -> set[str]:
    return _with_dependencies(set(permissions))


def effective_permissions(role: str, overrides: dict[str, Any] | None = None) -> set[str]:
    if role == "admin":
        return set(ALL_PERMISSIONS)
    overrides = overrides or {}
    if overrides.get("mode") == "explicit" or "allow" in overrides:
        return normalize_permission_selection(overrides.get("allow", []))
    denied = set(overrides.get("deny", []))
    return permissions_for_role(role) - denied


def validate_permission_selection(role: str, permissions: list[str]) -> set[str]:
    del role
    return set(permissions) & ALL_PERMISSIONS


def permission_overrides_from_selection(role: str, permissions: list[str]) -> dict[str, Any]:
    if role == "admin":
        return {"mode": "protected_admin", "allow": sorted(ALL_PERMISSIONS)}
    selected = normalize_permission_selection(validate_permission_selection(role, permissions))
    return {"mode": "explicit", "allow": sorted(selected)}


def permission_catalog() -> dict[str, Any]:
    return {
        "groups": {group: list(values) for group, values in PERMISSION_GROUPS.items()},
        "items": {permission: {"key": permission, **PERMISSION_METADATA[permission]} for permission in sorted(ALL_PERMISSIONS)},
        "role_permissions": {role: sorted(values) for role, values in ROLE_PERMISSIONS.items()},
    }


def permission_for_request(path: str, method: str) -> str | None:
    method = method.upper()
    if path.startswith("/api/dashboard"):
        return "dashboard.view"
    if path.startswith("/api/vehicles"):
        return "vehicles.view" if method == "GET" else ("vehicles.create" if method == "POST" else "vehicles.update")
    if path.startswith("/api/maintenance") or path.startswith("/api/inspections"):
        return "maintenance.view" if method == "GET" else "maintenance.manage"
    if path.startswith("/api/predictive-maintenance"):
        return "predictive.view" if method == "GET" else "predictive.run"
    if path.startswith("/api/demand"):
        if path.rstrip("/").endswith("/export"):
            return "reports.export"
        return "demand.view" if method == "GET" else "demand.refresh"
    if path.startswith("/api/deliveries"):
        return "deliveries.view" if method == "GET" else "deliveries.manage"
    if path.startswith("/api/load-optimization"):
        if path.rstrip("/").endswith("/export"):
            return "reports.export"
        if method == "GET":
            return "load_optimization.view"
        if path.endswith("/cancel") or path.endswith("/release"):
            return "load_optimization.cancel"
        if path.endswith("/approve"):
            return "load_optimization.approve"
        if path.endswith("/assign"):
            return "load_optimization.assign"
        return "load_optimization.generate"
    if path.startswith("/api/routes"):
        if method == "GET":
            return "routes.view"
        return "routes.dispatch" if path.endswith("/dispatch") else "routes.optimize"
    if path.startswith("/api/route-sets"):
        if method == "GET":
            return "routes.view"
        if path.endswith("/approve"):
            return "routes.approve"
        if path.endswith("/dispatch") or path.endswith("/assign-driver"):
            return "routes.dispatch"
        return "routes.optimize"
    if path.startswith("/api/live-trips"):
        return "live_trips.view"
    if path.startswith("/api/alerts"):
        return "alerts.view"
    if path.startswith("/api/intelligence"):
        return "readiness.view"
    if path.startswith("/api/reports"):
        if path.rstrip("/").endswith("/export"):
            return "reports.export"
        return "reports.view" if method == "GET" else "reports.export"
    return None
