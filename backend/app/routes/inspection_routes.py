from fastapi import APIRouter, Depends, Query

from app.middleware.auth_middleware import require_roles
from app.schemas.inspection_schema import (
    InspectionAssignRequest,
    InspectionCancelRequest,
    InspectionCompleteRequest,
    InspectionCreateRequest,
    InspectionDecisionRequest,
    InspectionDraftRequest,
    InspectionStartRequest,
)
from app.services.inspection_service import (
    INSPECTION_MANAGE_ROLES,
    INSPECTION_VIEW_ROLES,
    assign_inspection,
    cancel_inspection,
    complete_inspection,
    create_inspection,
    decide_inspection,
    get_inspection,
    list_inspection_assignees,
    list_inspections,
    save_inspection_draft,
    start_inspection,
)
from app.utils.response import success_response


router = APIRouter(prefix="/inspections", tags=["Vehicle Inspections"])


@router.get("")
async def inspection_list(
    status_filter: str | None = Query(default=None, alias="status"),
    vehicle_id: str | None = None,
    assigned_to: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: dict = Depends(require_roles(INSPECTION_VIEW_ROLES)),
):
    data = await list_inspections(status_filter, vehicle_id, assigned_to, page, limit)
    return success_response("Vehicle inspections retrieved", data=data)


@router.post("")
async def inspection_create(
    payload: InspectionCreateRequest,
    current_user: dict = Depends(require_roles(INSPECTION_MANAGE_ROLES)),
):
    return success_response(
        "Vehicle inspection created",
        data=await create_inspection(payload.model_dump(), current_user),
    )


@router.get("/assignees")
async def inspection_assignees(
    _: dict = Depends(require_roles(INSPECTION_VIEW_ROLES)),
):
    return success_response(
        "Inspection assignees retrieved",
        data={"items": await list_inspection_assignees()},
    )


@router.get("/{inspection_id}")
async def inspection_detail(
    inspection_id: str,
    _: dict = Depends(require_roles(INSPECTION_VIEW_ROLES)),
):
    return success_response("Vehicle inspection retrieved", data=await get_inspection(inspection_id))


@router.post("/{inspection_id}/assign")
async def inspection_assign(
    inspection_id: str,
    payload: InspectionAssignRequest,
    current_user: dict = Depends(require_roles(INSPECTION_MANAGE_ROLES)),
):
    return success_response(
        "Vehicle inspection assigned",
        data=await assign_inspection(inspection_id, payload.model_dump(), current_user),
    )


@router.post("/{inspection_id}/start")
async def inspection_start(
    inspection_id: str,
    payload: InspectionStartRequest,
    current_user: dict = Depends(require_roles(INSPECTION_MANAGE_ROLES)),
):
    return success_response(
        "Vehicle inspection started",
        data=await start_inspection(inspection_id, payload.model_dump(), current_user),
    )


@router.post("/{inspection_id}/complete")
async def inspection_complete(
    inspection_id: str,
    payload: InspectionCompleteRequest,
    current_user: dict = Depends(require_roles(INSPECTION_MANAGE_ROLES)),
):
    return success_response(
        "Vehicle inspection completed and is awaiting a service decision",
        data=await complete_inspection(inspection_id, payload.model_dump(), current_user),
    )


@router.patch("/{inspection_id}/draft")
async def inspection_draft(
    inspection_id: str,
    payload: InspectionDraftRequest,
    current_user: dict = Depends(require_roles(INSPECTION_MANAGE_ROLES)),
):
    return success_response(
        "Inspection draft saved",
        data=await save_inspection_draft(
            inspection_id,
            payload.model_dump(exclude_unset=True),
            current_user,
        ),
    )


@router.post("/{inspection_id}/cancel")
async def inspection_cancel(
    inspection_id: str,
    payload: InspectionCancelRequest,
    current_user: dict = Depends(require_roles(INSPECTION_MANAGE_ROLES)),
):
    return success_response(
        "Vehicle inspection cancelled",
        data=await cancel_inspection(inspection_id, payload.model_dump(), current_user),
    )


@router.post("/{inspection_id}/decision")
async def inspection_decision(
    inspection_id: str,
    payload: InspectionDecisionRequest,
    current_user: dict = Depends(require_roles(INSPECTION_MANAGE_ROLES)),
):
    return success_response(
        "Inspection decision recorded",
        data=await decide_inspection(inspection_id, payload.model_dump(), current_user),
    )
