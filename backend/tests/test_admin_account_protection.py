import pytest
from fastapi import HTTPException

from app.services.user_service import assert_account_update_allowed


@pytest.mark.parametrize("update", [
    {"role": "fleet_manager"},
    {"is_active": False},
    {"permission_overrides": {"mode": "explicit", "allow": []}},
])
def test_admin_security_properties_are_immutable(update: dict) -> None:
    with pytest.raises(HTTPException) as exc:
        assert_account_update_allowed({"role": "admin", "is_active": True}, update)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Administrator access and account status are protected"


def test_admin_profile_fields_remain_editable() -> None:
    assert_account_update_allowed({"role": "admin", "is_active": True}, {"full_name": "Primary Administrator"})
