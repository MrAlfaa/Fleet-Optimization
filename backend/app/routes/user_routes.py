from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.auth_middleware import get_current_user, require_admin, require_roles
from app.core.permissions import permission_catalog
from app.schemas.user_schema import UserCreate, UserPermissionUpdate, UserUpdate
from app.services.user_service import (
    activate_user,
    create_user,
    deactivate_user,
    get_user_by_id,
    list_users,
    update_user,
    update_user_permissions,
)
from app.utils.response import success_response
from app.utils.validators import validate_user_role
from app.schemas.driver_device_schema import DriverAdminCreate, DriverAdminUpdate, DriverDeviceResetRequest
from app.services.driver_device_service import create_driver_by_admin, list_drivers_for_admin, reset_driver_device, update_driver_by_admin


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/permissions/catalog")
async def get_permissions_catalog(_: dict = Depends(require_admin)) -> dict:
    return success_response("Permission catalog loaded successfully", data=permission_catalog())


@router.put("/{user_id}/permissions")
async def set_user_permissions(
    user_id: str,
    payload: UserPermissionUpdate,
    _: dict = Depends(require_admin),
) -> dict:
    data = await update_user_permissions(user_id, payload.permissions)
    return success_response("User permissions updated successfully", data=data)


@router.get("/drivers/manage")
async def manage_drivers(_: dict = Depends(require_admin)) -> dict:
    return success_response("Drivers loaded successfully", data=await list_drivers_for_admin())


@router.post("/drivers")
async def create_driver(payload: DriverAdminCreate, _: dict = Depends(require_admin)) -> dict:
    return success_response("Driver created successfully", data=await create_driver_by_admin(payload.model_dump()))


@router.put("/drivers/{driver_id}")
async def update_driver_admin(driver_id: str, payload: DriverAdminUpdate, _: dict = Depends(require_admin)) -> dict:
    return success_response("Driver updated successfully", data=await update_driver_by_admin(driver_id, payload.model_dump(exclude_unset=True)))


@router.post("/drivers/{driver_id}/reset-device")
async def reset_device(driver_id: str, payload: DriverDeviceResetRequest, admin: dict = Depends(require_admin)) -> dict:
    return success_response("Driver device reset successfully", data=await reset_driver_device(driver_id, payload.temporary_password, admin))


@router.patch("/drivers/{driver_id}/activate")
async def activate_driver(driver_id: str, _: dict = Depends(require_admin)) -> dict:
    return success_response("Driver activated successfully", data=await activate_user(driver_id))


@router.patch("/drivers/{driver_id}/deactivate")
async def deactivate_driver(driver_id: str, _: dict = Depends(require_admin)) -> dict:
    return success_response("Driver deactivated successfully", data=await deactivate_user(driver_id))


@router.get("")
async def get_users(
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: dict = Depends(require_admin),
) -> dict:
    if role:
        validate_user_role(role)
    data = await list_users(role=role, is_active=is_active, search=search, page=page, limit=limit)
    return success_response("Users loaded successfully", data=data)


@router.get("/drivers/list")
async def get_active_drivers(
    user: dict = Depends(require_roles(["admin", "fleet_manager", "route_planner"])),
) -> dict:
    data = await list_drivers_for_admin()
    active = [driver for driver in data if driver.get("is_active") and driver.get("device_enrollment_status") == "enrolled"]
    return success_response("Active enrolled drivers loaded successfully", data=active)


@router.post("")
async def add_user(payload: UserCreate, _: dict = Depends(require_admin)) -> dict:
    data = await create_user(payload.model_dump())
    return success_response("User created successfully", data=data)


@router.get("/{user_id}")
async def get_user_detail(user_id: str, current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another user's profile")

    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return success_response("User loaded successfully", data=user)


@router.put("/{user_id}")
async def edit_user(
    user_id: str,
    payload: UserUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    update_data = payload.model_dump(exclude_unset=True)
    if current_user["role"] != "admin":
        if current_user["id"] != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update another user")
        allowed_fields = {"full_name", "phone"}
        update_data = {key: value for key, value in update_data.items() if key in allowed_fields}

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid update fields provided")

    user = await update_user(user_id, update_data)
    return success_response("User updated successfully", data=user)


@router.patch("/{user_id}/deactivate")
async def deactivate_user_account(user_id: str, _: dict = Depends(require_admin)) -> dict:
    user = await deactivate_user(user_id)
    return success_response("User deactivated successfully", data=user)


@router.patch("/{user_id}/activate")
async def activate_user_account(user_id: str, _: dict = Depends(require_admin)) -> dict:
    user = await activate_user(user_id)
    return success_response("User activated successfully", data=user)
