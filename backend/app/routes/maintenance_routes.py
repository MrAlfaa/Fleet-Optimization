from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.auth_middleware import require_roles
from app.models.maintenance_model import MAINTENANCE_PRIORITIES, MAINTENANCE_STATUSES, MAINTENANCE_TYPES
from app.schemas.maintenance_schema import MaintenanceCompleteRequest, MaintenanceRecordCreate, MaintenanceRecordUpdate
from app.services.maintenance_service import (
    cancel_maintenance_record,
    complete_maintenance_record,
    create_maintenance_record,
    get_maintenance_record_by_id,
    get_maintenance_summary,
    list_maintenance_records,
    update_maintenance_record,
)
from app.utils.response import success_response
from app.utils.validators import validate_choice


router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


@router.get("")
async def get_maintenance_records(
    vehicle_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    maintenance_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager"])),
) -> dict:
    if status:
        validate_choice(status, MAINTENANCE_STATUSES, "Maintenance status")
    if priority:
        validate_choice(priority, MAINTENANCE_PRIORITIES, "Priority")
    if maintenance_type:
        validate_choice(maintenance_type, MAINTENANCE_TYPES, "Maintenance type")
    data = await list_maintenance_records(vehicle_id, status, priority, maintenance_type, search, page, limit)
    return success_response("Maintenance records retrieved successfully", data=data)


@router.post("")
async def add_maintenance_record(
    payload: MaintenanceRecordCreate,
    current_user: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager"])),
) -> dict:
    data = await create_maintenance_record(payload.model_dump(), current_user)
    return success_response("Maintenance record created successfully", data=data)


@router.get("/summary/overview")
async def maintenance_summary(_: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager"]))) -> dict:
    data = await get_maintenance_summary()
    return success_response("Maintenance summary retrieved successfully", data=data)


@router.get("/{record_id}")
async def get_maintenance_record(
    record_id: str,
    _: dict = Depends(require_roles(["admin", "fleet_manager", "maintenance_manager"])),
) -> dict:
    data = await get_maintenance_record_by_id(record_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found")
    return success_response("Maintenance record retrieved successfully", data=data)


@router.put("/{record_id}")
async def edit_maintenance_record(
    record_id: str,
    payload: MaintenanceRecordUpdate,
    _: dict = Depends(require_roles(["admin", "maintenance_manager"])),
) -> dict:
    data = await update_maintenance_record(record_id, payload.model_dump(exclude_unset=True))
    return success_response("Maintenance record updated successfully", data=data)


@router.patch("/{record_id}/complete")
async def complete_record(
    record_id: str,
    payload: MaintenanceCompleteRequest,
    current_user: dict = Depends(require_roles(["admin", "maintenance_manager"])),
) -> dict:
    data = await complete_maintenance_record(record_id, payload.model_dump(exclude_unset=True), current_user)
    return success_response("Maintenance record completed successfully", data=data)


@router.patch("/{record_id}/cancel")
async def cancel_record(record_id: str, _: dict = Depends(require_roles(["admin", "maintenance_manager"]))) -> dict:
    data = await cancel_maintenance_record(record_id)
    return success_response("Maintenance record cancelled successfully", data=data)
