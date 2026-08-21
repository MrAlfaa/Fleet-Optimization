from app.core.permissions import effective_permissions, permissions_for_role, validate_permission_selection


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


def test_permission_selection_cannot_exceed_role_authority() -> None:
    selected = validate_permission_selection("maintenance_manager", ["maintenance.manage", "routes.dispatch"])

    assert selected == {"maintenance.manage"}

