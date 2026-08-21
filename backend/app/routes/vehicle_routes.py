from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.middleware.auth_middleware import require_admin, require_roles
from app.models.vehicle_model import VEHICLE_HEALTH_STATUSES, VEHICLE_STATUSES
from app.models.vehicle_part_model import get_ev_part_catalog
from app.schemas.vehicle_part_schema import VehiclePartCreate, VehiclePartLifecycleRequest, VehiclePartUpdate
from app.schemas.vehicle_schema import VehicleCreate, VehicleLifecycleRequest, VehicleUpdate
from app.services.vehicle_part_service import (
    archive_vehicle_part,
    create_vehicle_part,
    get_parts_by_vehicle,
    restore_vehicle_part,
    update_vehicle_part,
)
from app.services.vehicle_service import (
    assign_driver,
    create_vehicle,
    get_vehicle_by_id,
    list_vehicles,
    restore_vehicle,
    retire_vehicle,
    update_vehicle,
)
from app.services.vehicle_media_service import delete_vehicle_image, save_vehicle_image
from app.utils.response import success_response
from app.utils.validators import validate_choice


router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.get("")
async def get_vehicles(
    status: str | None = Query(default=None),
    health_status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager"])),
) -> dict:
    if status:
        validate_choice(status, VEHICLE_STATUSES, "Vehicle status")
    if health_status:
        validate_choice(health_status, VEHICLE_HEALTH_STATUSES, "Health status")
    data = await list_vehicles(status_filter=status, health_status=health_status, search=search, page=page, limit=limit)
    return success_response("Vehicles retrieved successfully", data=data)


@router.post("")
async def add_vehicle(
    payload: VehicleCreate,
    current_user: dict = Depends(require_roles(["admin", "fleet_manager"])),
) -> dict:
    data = await create_vehicle(payload.model_dump(), current_user)
    return success_response("Vehicle created successfully", data=data)


@router.get("/parts/catalog")
async def get_vehicle_part_catalog(
    _: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager", "route_planner"])),
) -> dict:
    return success_response("EV parts catalogue retrieved successfully", data=get_ev_part_catalog())


@router.post("/{vehicle_id}/image")
async def upload_vehicle_image(
    vehicle_id: str,
    image: UploadFile = File(...),
    _: dict = Depends(require_roles(["admin", "fleet_manager"])),
) -> dict:
    data = await save_vehicle_image(vehicle_id, image)
    return success_response("Vehicle image uploaded successfully", data=data)


@router.delete("/{vehicle_id}/image")
async def remove_vehicle_image(
    vehicle_id: str,
    _: dict = Depends(require_roles(["admin", "fleet_manager"])),
) -> dict:
    data = await delete_vehicle_image(vehicle_id)
    return success_response("Vehicle image removed successfully", data=data)


@router.put("/parts/{part_id}")
async def edit_vehicle_part(
    part_id: str,
    payload: VehiclePartUpdate,
    _: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager"])),
) -> dict:
    update_data = payload.model_dump(exclude_unset=True)
    update_data.pop("risk_level", None)
    update_data.pop("risk_score", None)
    data = await update_vehicle_part(part_id, update_data)
    return success_response("Vehicle part updated successfully", data=data)


@router.get("/{vehicle_id}/parts")
async def get_vehicle_parts(
    vehicle_id: str,
    include_archived: bool = Query(default=False),
    _: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager", "route_planner"])),
) -> dict:
    data = await get_parts_by_vehicle(vehicle_id, include_archived=include_archived)
    return success_response("Vehicle parts retrieved successfully", data=data)


@router.post("/{vehicle_id}/parts")
async def add_vehicle_part(
    vehicle_id: str,
    payload: VehiclePartCreate,
    _: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager"])),
) -> dict:
    data = await create_vehicle_part(vehicle_id, payload.model_dump())
    return success_response("Vehicle part created successfully", data=data)


@router.patch("/{vehicle_id}/assign-driver/{driver_id}")
async def assign_vehicle_driver(
    vehicle_id: str,
    driver_id: str,
    _: dict = Depends(require_roles(["admin", "fleet_manager"])),
) -> dict:
    data = await assign_driver(vehicle_id, driver_id)
    return success_response("Driver assigned successfully", data=data)


@router.get("/{vehicle_id}")
async def get_vehicle_detail(
    vehicle_id: str,
    _: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager", "route_planner"])),
) -> dict:
    data = await get_vehicle_by_id(vehicle_id)
    if data is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return success_response("Vehicle retrieved successfully", data=data)


@router.put("/{vehicle_id}")
async def edit_vehicle(
    vehicle_id: str,
    payload: VehicleUpdate,
    _: dict = Depends(require_roles(["admin", "fleet_manager"])),
) -> dict:
    data = await update_vehicle(vehicle_id, payload.model_dump(exclude_unset=True))
    return success_response("Vehicle updated successfully", data=data)


@router.post("/parts/{part_id}/archive")
async def archive_part(
    part_id: str,
    payload: VehiclePartLifecycleRequest,
    current_user: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager"])),
) -> dict:
    data = await archive_vehicle_part(part_id, current_user, payload.reason)
    return success_response("Vehicle part archived successfully", data=data)


@router.post("/parts/{part_id}/restore")
async def restore_part(
    part_id: str,
    _: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager"])),
) -> dict:
    data = await restore_vehicle_part(part_id)
    return success_response("Vehicle part restored successfully", data=data)


@router.post("/{vehicle_id}/retire")
async def retire_vehicle_route(
    vehicle_id: str,
    payload: VehicleLifecycleRequest,
    current_user: dict = Depends(require_roles(["admin", "fleet_manager"])),
) -> dict:
    data = await retire_vehicle(vehicle_id, current_user, payload.reason)
    return success_response("Vehicle retired successfully", data=data)


@router.post("/{vehicle_id}/restore")
async def restore_vehicle_route(
    vehicle_id: str,
    _: dict = Depends(require_roles(["admin", "fleet_manager"])),
) -> dict:
    data = await restore_vehicle(vehicle_id)
    return success_response("Vehicle restored as inactive successfully", data=data)


@router.delete("/{vehicle_id}")
async def retire_vehicle_legacy(vehicle_id: str, current_user: dict = Depends(require_admin)) -> dict:
    data = await retire_vehicle(vehicle_id, current_user)
    return success_response("Vehicle retired successfully", data=data)
