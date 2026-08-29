from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.middleware.auth_middleware import require_roles
from app.schemas.load_optimization_schema import (
    LoadOptimizationJobCreate,
    LoadPlanApproval,
    ParcelConsolidationCreate,
    PhysicalVehicleAssignment,
)
from app.services.load_optimization_service import (
    approve_load_plan,
    assign_physical_vehicle,
    cancel_optimization_job,
    create_optimization_job,
    create_parcel_consolidation,
    export_load_plan_csv,
    get_batch_consolidation,
    get_batch_eligibility,
    get_consolidation_planning_state,
    get_parcel_consolidation,
    get_load_plan,
    get_optimization_job,
    get_vehicle_suggestions,
    get_vehicle_type_catalog,
    list_load_plans,
    list_parcel_consolidations,
    release_load_plan,
)
from app.utils.response import success_response


router = APIRouter(prefix="/load-optimization", tags=["Load Optimization"])
ALLOWED_ROLES = ["admin", "fleet_manager", "route_planner"]


@router.get("/eligibility")
async def eligibility(
    delivery_date: date,
    delivery_period: str = Query(pattern="^(first_half|second_half)$"),
    _: dict = Depends(require_roles(ALLOWED_ROLES)),
) -> dict:
    return success_response("Load planning eligibility retrieved", data=await get_batch_eligibility(str(delivery_date), delivery_period))


@router.get("/consolidation")
async def consolidation(
    delivery_date: date,
    delivery_period: str = Query(pattern="^(first_half|second_half)$"),
    _: dict = Depends(require_roles(ALLOWED_ROLES)),
) -> dict:
    return success_response(
        "Parcel consolidation snapshot retrieved",
        data=await get_batch_consolidation(str(delivery_date), delivery_period),
    )


@router.post("/consolidations")
async def create_consolidation(
    payload: ParcelConsolidationCreate,
    current_user: dict = Depends(require_roles(ALLOWED_ROLES)),
) -> dict:
    return success_response(
        "Parcel consolidation created",
        data=await create_parcel_consolidation(payload.model_dump(), current_user),
    )


@router.get("/consolidations")
async def consolidations(
    delivery_date: date | None = None,
    delivery_period: str | None = Query(default=None, pattern="^(first_half|second_half)$"),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    _: dict = Depends(require_roles(ALLOWED_ROLES)),
) -> dict:
    items = await list_parcel_consolidations(
        delivery_date=str(delivery_date) if delivery_date else None,
        delivery_period=delivery_period,
        status_filter=status_filter,
        search=search,
    )
    return success_response("Parcel consolidations retrieved", data={"items": items, "total": len(items)})


@router.get("/consolidations/{consolidation_id}")
async def consolidation_detail(
    consolidation_id: str,
    _: dict = Depends(require_roles(ALLOWED_ROLES)),
) -> dict:
    item = await get_parcel_consolidation(consolidation_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcel consolidation not found")
    return success_response("Parcel consolidation retrieved", data=item)


@router.get("/consolidations/{consolidation_id}/planning-state")
async def consolidation_planning_state(
    consolidation_id: str,
    _: dict = Depends(require_roles(ALLOWED_ROLES)),
) -> dict:
    item = await get_consolidation_planning_state(consolidation_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active parcel consolidation not found")
    return success_response("Consolidation planning state retrieved", data=item)


@router.get("/vehicle-types")
async def vehicle_types(_: dict = Depends(require_roles(ALLOWED_ROLES))) -> dict:
    return success_response("Load vehicle type catalog retrieved", data=await get_vehicle_type_catalog())


@router.post("/jobs")
async def create_job(payload: LoadOptimizationJobCreate, current_user: dict = Depends(require_roles(ALLOWED_ROLES))) -> dict:
    return success_response("Load optimization job queued", data=await create_optimization_job(payload.model_dump(), current_user))


@router.get("/jobs/{job_id}")
async def job_detail(job_id: str, _: dict = Depends(require_roles(ALLOWED_ROLES))) -> dict:
    job = await get_optimization_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load optimization job not found")
    return success_response("Load optimization job retrieved", data=job)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, current_user: dict = Depends(require_roles(ALLOWED_ROLES))) -> dict:
    return success_response("Load optimization job cancelled", data=await cancel_optimization_job(job_id, current_user))


@router.get("/plans")
async def plans(
    delivery_date: date | None = None,
    delivery_period: str | None = Query(default=None, pattern="^(first_half|second_half)$"),
    status: str | None = None,
    consolidation_id: str | None = None,
    _: dict = Depends(require_roles(ALLOWED_ROLES)),
) -> dict:
    return success_response("Load plans retrieved", data={"items": await list_load_plans(delivery_date=str(delivery_date) if delivery_date else None, delivery_period=delivery_period, status_filter=status, consolidation_id=consolidation_id)})


@router.get("/plans/{plan_id}")
async def plan_detail(plan_id: str, _: dict = Depends(require_roles(ALLOWED_ROLES))) -> dict:
    plan = await get_load_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load plan not found")
    return success_response("Load plan retrieved", data=plan)


@router.post("/plans/{plan_id}/approve")
async def approve(plan_id: str, payload: LoadPlanApproval, current_user: dict = Depends(require_roles(ALLOWED_ROLES))) -> dict:
    return success_response("Load plan approved", data=await approve_load_plan(plan_id, payload.option_id, current_user))


@router.get("/plans/{plan_id}/vehicle-suggestions")
async def suggestions(plan_id: str, _: dict = Depends(require_roles(ALLOWED_ROLES))) -> dict:
    return success_response("Compatible vehicles retrieved", data=await get_vehicle_suggestions(plan_id))


@router.post("/plans/{plan_id}/loads/{load_id}/assign")
async def assign(
    plan_id: str, load_id: str, payload: PhysicalVehicleAssignment,
    current_user: dict = Depends(require_roles(ALLOWED_ROLES)),
) -> dict:
    return success_response("Physical vehicle assigned", data=await assign_physical_vehicle(plan_id, load_id, payload.vehicle_id, current_user))


@router.post("/plans/{plan_id}/release")
async def release(plan_id: str, current_user: dict = Depends(require_roles(ALLOWED_ROLES))) -> dict:
    return success_response("Load plan released", data=await release_load_plan(plan_id, current_user))


@router.get("/plans/{plan_id}/export")
async def export(plan_id: str, _: dict = Depends(require_roles(ALLOWED_ROLES))) -> StreamingResponse:
    return StreamingResponse(
        iter([await export_load_plan_csv(plan_id)]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={plan_id}.csv"},
    )
