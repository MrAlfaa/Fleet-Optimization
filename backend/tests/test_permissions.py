from app.core.permissions import (
    effective_permissions,
    normalize_permission_selection,
    permission_overrides_from_selection,
    permission_for_request,
    permissions_for_role,
    validate_permission_selection,
)


def test_admin_always_has_every_permission() -> None:
    assert effective_permissions("admin", {"deny": ["dashboard.view"]}) == permissions_for_role("admin")


def test_role_permissions_can_be_restricted_per_user() -> None:
    permissions = effective_permissions(
        "fleet_manager",
        {"deny": ["routes.dispatch", "maintenance.manage"]},
    )

    assert "dashboard.view" in permissions
    assert "routes.dispatch" not in permissions
    assert "maintenance.manage" not in permissions


def test_permission_selection_is_not_capped_by_role() -> None:
    selected = validate_permission_selection("maintenance_manager", ["maintenance.manage", "routes.dispatch"])

    assert selected == {"maintenance.manage", "routes.dispatch"}


def test_explicit_permissions_replace_role_template() -> None:
    overrides = permission_overrides_from_selection(
        "maintenance_manager",
        ["routes.dispatch", "vehicles.tab.activity"],
    )

    permissions = effective_permissions("maintenance_manager", overrides)

    assert "routes.dispatch" in permissions
    assert "routes.view" in permissions
    assert "vehicles.tab.activity" in permissions
    assert "vehicles.view" in permissions
    assert "maintenance.manage" not in permissions


def test_permission_dependencies_are_added_server_side() -> None:
    selected = normalize_permission_selection(["vehicles.tab.risk_assessment", "reports.export"])

    assert selected == {
        "vehicles.view",
        "vehicles.tab.risk_assessment",
        "reports.view",
        "reports.export",
    }


def test_unknown_permissions_are_rejected_from_selection() -> None:
    assert validate_permission_selection("fleet_manager", ["dashboard.view", "system.root"]) == {"dashboard.view"}


def test_get_exports_require_export_permission() -> None:
    assert permission_for_request("/api/reports/export", "GET") == "reports.export"
    assert permission_for_request("/api/demand/export", "GET") == "reports.export"
    assert permission_for_request("/api/demand/forecasts", "GET") == "demand.view"


def test_load_optimization_actions_have_distinct_permissions() -> None:
    assert permission_for_request("/api/load-optimization/eligibility", "GET") == "load_optimization.view"
    assert permission_for_request("/api/load-optimization/jobs", "POST") == "load_optimization.generate"
    assert permission_for_request("/api/load-optimization/jobs/job-1/cancel", "POST") == "load_optimization.cancel"
    assert permission_for_request("/api/load-optimization/plans/plan-1/approve", "POST") == "load_optimization.approve"
    assert permission_for_request("/api/load-optimization/plans/plan-1/loads/load-1/assign", "POST") == "load_optimization.assign"
    assert permission_for_request("/api/load-optimization/plans/plan-1/export", "GET") == "reports.export"
