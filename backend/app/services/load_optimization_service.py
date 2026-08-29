from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from fastapi import HTTPException, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.database import get_database
from app.models.delivery_model import DELIVERY_COLLECTION, safe_delivery_document
from app.models.load_optimization_model import (
    LOAD_SEQUENCE_COUNTERS_COLLECTION,
    LOAD_OPTIMIZATION_JOBS_COLLECTION,
    LOAD_OPTIMIZATION_PLANS_COLLECTION,
    PARCEL_CONSOLIDATIONS_COLLECTION,
    build_batch_fingerprint,
    build_consolidation_document,
    build_consolidation_id,
    build_optimization_job_document,
    safe_load_document,
    validate_plan_transition,
)
from app.models.user_model import utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION, safe_vehicle_document
from app.utils.object_id import validate_object_id


DEFAULT_VEHICLE_TYPE_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "code": "COMPACT_CAR",
        "label": "Compact cargo car",
        "category": "car",
        "capacity_kg": 350.0,
        "capacity_m3": 1.8,
        "max_parcels": 18,
        "max_stack_layers": 2,
        "max_stack_weight_kg": 60.0,
        "cargo_length_cm": 160.0,
        "cargo_width_cm": 105.0,
        "cargo_height_cm": 105.0,
        "is_refrigerated": False,
        "is_hazmat_certified": False,
    },
    {
        "code": "MEDIUM_VAN",
        "label": "Medium cargo van",
        "category": "van",
        "capacity_kg": 1_200.0,
        "capacity_m3": 8.5,
        "max_parcels": 70,
        "max_stack_layers": 4,
        "max_stack_weight_kg": 300.0,
        "cargo_length_cm": 320.0,
        "cargo_width_cm": 175.0,
        "cargo_height_cm": 170.0,
        "is_refrigerated": False,
        "is_hazmat_certified": False,
    },
    {
        "code": "MEDIUM_VAN_REEFER",
        "label": "Refrigerated medium van",
        "category": "van",
        "capacity_kg": 1_100.0,
        "capacity_m3": 7.5,
        "max_parcels": 60,
        "max_stack_layers": 4,
        "max_stack_weight_kg": 250.0,
        "cargo_length_cm": 310.0,
        "cargo_width_cm": 170.0,
        "cargo_height_cm": 160.0,
        "is_refrigerated": True,
        "temp_min_celsius": -18.0,
        "temp_max_celsius": 12.0,
        "is_hazmat_certified": False,
    },
    {
        "code": "MEDIUM_TRUCK",
        "label": "Medium box truck",
        "category": "truck",
        "capacity_kg": 4_500.0,
        "capacity_m3": 24.0,
        "max_parcels": 180,
        "max_stack_layers": 6,
        "max_stack_weight_kg": 900.0,
        "cargo_length_cm": 540.0,
        "cargo_width_cm": 220.0,
        "cargo_height_cm": 210.0,
        "is_refrigerated": False,
        "is_hazmat_certified": False,
    },
    {
        "code": "HAZMAT_TRUCK",
        "label": "Certified hazardous-load truck",
        "category": "truck",
        "capacity_kg": 4_000.0,
        "capacity_m3": 20.0,
        "max_parcels": 120,
        "max_stack_layers": 4,
        "max_stack_weight_kg": 750.0,
        "cargo_length_cm": 520.0,
        "cargo_width_cm": 215.0,
        "cargo_height_cm": 190.0,
        "is_refrigerated": False,
        "is_hazmat_certified": True,
    },
    {
        "code": "HEAVY_BUS",
        "label": "Converted logistics bus",
        "category": "bus",
        "capacity_kg": 3_000.0,
        "capacity_m3": 18.0,
        "max_parcels": 140,
        "max_stack_layers": 5,
        "max_stack_weight_kg": 600.0,
        "cargo_length_cm": 600.0,
        "cargo_width_cm": 210.0,
        "cargo_height_cm": 190.0,
        "is_refrigerated": False,
        "is_hazmat_certified": False,
    },
)


def build_vehicle_type_catalog_view(
    catalog: Iterable[dict[str, Any]], vehicles: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, int]] = {}
    for vehicle in vehicles:
        profile_code = str((vehicle.get("load_profile") or {}).get("profile_code") or "").upper()
        if not profile_code:
            continue
        item = counts.setdefault(profile_code, {"registered": 0, "active": 0})
        item["registered"] += 1
        if vehicle.get("status") == "active":
            item["active"] += 1
    return [
        {
            **dict(vehicle_type),
            "registered_vehicle_count": counts.get(str(vehicle_type.get("code") or "").upper(), {}).get("registered", 0),
            "active_vehicle_count": counts.get(str(vehicle_type.get("code") or "").upper(), {}).get("active", 0),
        }
        for vehicle_type in catalog
    ]


def _id(document: dict[str, Any]) -> str:
    return str(document.get("id") or document.get("_id") or document.get("order_code") or "")


def assess_batch_orders(
    orders: Iterable[dict[str, Any]],
    delivery_date: str,
    delivery_period: str,
    *,
    allowed_planning_statuses: set[str] | None = None,
    consolidation_id: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    eligible_orders: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    excluded_orders: list[dict[str, Any]] = []

    allowed_statuses = allowed_planning_statuses or {"unplanned", "failed"}
    for order in orders:
        exclusion_reasons: list[str] = []
        if str(order.get("delivery_date")) != delivery_date:
            exclusion_reasons.append("delivery_date_mismatch")
        if order.get("delivery_period") != delivery_period:
            exclusion_reasons.append("delivery_period_mismatch")
        if order.get("delivery_status") != "pending":
            exclusion_reasons.append(f"delivery_status_{order.get('delivery_status') or 'unknown'}")
        planning_status = order.get("load_planning_status") or "unplanned"
        if planning_status not in allowed_statuses:
            exclusion_reasons.append(f"load_planning_status_{planning_status}")
        if consolidation_id and str(order.get("active_consolidation_id") or "") != consolidation_id:
            exclusion_reasons.append("consolidation_id_mismatch")

        profile = order.get("load_profile") or {}
        validation_reasons: list[str] = []
        if not profile.get("optimization_eligible"):
            profile_reasons = profile.get("eligibility_reasons") or ["load_profile_ineligible"]
            validation_reasons.extend(str(reason) for reason in profile_reasons)

        if validation_reasons:
            exceptions.append({"order_id": _id(order), "reasons": sorted(set(validation_reasons))})
        elif exclusion_reasons:
            excluded_orders.append({"order_id": _id(order), "reasons": sorted(set(exclusion_reasons))})
        else:
            eligible_orders.append(order)

    eligible_orders.sort(key=_id)
    exceptions.sort(key=lambda item: item["order_id"])
    excluded_orders.sort(key=lambda item: item["order_id"])
    return {"eligible_orders": eligible_orders, "exceptions": exceptions, "excluded_orders": excluded_orders}


def candidate_generation_state(
    *, job: dict[str, Any] | None, plan: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return the once-only generation state for one parcel consolidation."""
    plan_status = str((plan or {}).get("status") or "")
    if plan_status == "approved":
        return {"status": "approved", "can_generate": False, "can_retry": False}
    if plan_status == "review_required":
        return {"status": "ready", "can_generate": False, "can_retry": False}

    job_status = str((job or {}).get("status") or "")
    if job_status in {"queued", "running"}:
        return {"status": job_status, "can_generate": False, "can_retry": False}
    if job_status in {"failed", "cancelled"}:
        return {"status": job_status, "can_generate": True, "can_retry": True}
    if job_status == "completed":
        return {"status": "completed", "can_generate": False, "can_retry": False}
    return {"status": "not_started", "can_generate": True, "can_retry": False}


def vehicle_supports_virtual_load(vehicle: dict[str, Any], virtual_load: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    profile = vehicle.get("load_profile") or {}

    if vehicle.get("status") != "active":
        reasons.append("Vehicle is not active")
    if vehicle.get("dispatch_hold"):
        reasons.append("Vehicle has a dispatch hold")

    payload_capacity = vehicle.get("payload_capacity_kg") or profile.get("capacity_kg") or 0
    if float(payload_capacity) < float(virtual_load.get("used_weight_kg") or 0):
        reasons.append("Payload capacity is insufficient")
    if float(profile.get("capacity_m3") or 0) < float(virtual_load.get("used_volume_m3") or 0):
        reasons.append("Cargo volume capacity is insufficient")
    if int(profile.get("max_parcels") or 0) < int(virtual_load.get("parcel_count") or 0):
        reasons.append("Maximum parcel count is insufficient")
    planned_bay = (
        float(virtual_load.get("cargo_length_cm") or 0),
        float(virtual_load.get("cargo_width_cm") or 0),
        float(virtual_load.get("cargo_height_cm") or 0),
    )
    physical_bay = (
        float(profile.get("cargo_length_cm") or 0),
        float(profile.get("cargo_width_cm") or 0),
        float(profile.get("cargo_height_cm") or 0),
    )
    if any(actual < planned for actual, planned in zip(physical_bay, planned_bay, strict=True)):
        reasons.append("Physical cargo bay dimensions are smaller than the approved placement plan")

    if virtual_load.get("requires_refrigeration"):
        if not profile.get("is_refrigerated"):
            reasons.append("Refrigeration capability is required")
        else:
            vehicle_min = profile.get("temp_min_celsius")
            vehicle_max = profile.get("temp_max_celsius")
            load_min = virtual_load.get("temp_min_celsius")
            load_max = virtual_load.get("temp_max_celsius")
            if (
                vehicle_min is None
                or vehicle_max is None
                or load_min is None
                or load_max is None
                or float(vehicle_min) > float(load_min)
                or float(vehicle_max) < float(load_max)
            ):
                reasons.append("Vehicle temperature range does not cover the load requirement")

    if virtual_load.get("hazardous") and not profile.get("is_hazmat_certified"):
        reasons.append("Hazmat certification is required")

    return {"eligible": not reasons, "reasons": reasons}


def public_readiness_summary(readiness: dict[str, Any]) -> dict[str, Any]:
    return {
        "eligible": bool(readiness.get("eligible")),
        "blocking_reasons": [str(item) for item in readiness.get("blocking_reasons") or []],
        "warnings": [str(item) for item in readiness.get("warnings") or []],
    }


def validate_route_handoff(
    plan: dict[str, Any], load_id: str, vehicle_id: str, order_ids: Iterable[str],
) -> dict[str, Any]:
    if plan.get("status") != "approved":
        raise ValueError("Only an approved load plan can be routed")
    load = next(
        (item for item in (plan.get("selected_option") or {}).get("loads", []) if item.get("load_id") == load_id),
        None,
    )
    if load is None:
        raise ValueError("The selected virtual load does not exist in this plan")
    if str(load.get("assigned_vehicle_id") or "") != str(vehicle_id):
        raise ValueError("Route vehicle must match the confirmed physical vehicle")
    if set(str(value) for value in load.get("parcel_ids", [])) != set(str(value) for value in order_ids):
        raise ValueError("Route request must contain the exact parcel set from the approved virtual load")
    return load


def selected_parcel_load_map(selected_option: dict[str, Any]) -> dict[str, str]:
    assignments: dict[str, str] = {}
    exception_ids = {
        str(item.get("parcel_id"))
        for item in selected_option.get("exceptions") or []
        if item.get("parcel_id")
    }
    for load in selected_option.get("loads") or []:
        load_id = str(load.get("load_id") or "").strip()
        if not load_id:
            raise ValueError("Every selected load requires a load ID")
        for value in load.get("parcel_ids") or []:
            parcel_id = str(value)
            if parcel_id in exception_ids:
                raise ValueError("An exception parcel cannot be assigned to a selected load")
            if parcel_id in assignments:
                raise ValueError("A parcel cannot be assigned to more than one selected load")
            assignments[parcel_id] = load_id
    return assignments


async def synchronize_approved_plan_deliveries(plan: dict[str, Any]) -> None:
    if plan.get("status") != "approved":
        raise ValueError("Only an approved load plan can synchronize parcel assignments")
    database = _database()
    selected = plan.get("selected_option") or {}
    assignments = selected_parcel_load_map(selected)
    plan_id = str(plan["plan_id"])
    now = utc_now()
    loads_by_id = {
        str(load.get("load_id")): load
        for load in selected.get("loads") or []
        if load.get("load_id")
    }

    for load_id, load in loads_by_id.items():
        parcel_ids = [
            validate_object_id(parcel_id)
            for parcel_id, assigned_load_id in assignments.items()
            if assigned_load_id == load_id
        ]
        if not parcel_ids:
            continue
        vehicle_id = load.get("assigned_vehicle_id")
        await database[DELIVERY_COLLECTION].update_many(
            {
                "_id": {"$in": parcel_ids},
                "delivery_status": "pending",
                "load_planning_status": {"$in": ["consolidated", "failed", "planned", "vehicle_assigned"]},
            },
            {
                "$set": {
                    "load_planning_status": "vehicle_assigned" if vehicle_id else "planned",
                    "active_load_plan_id": plan_id,
                    "active_load_id": load_id,
                    "load_reservation_job_id": None,
                    "assigned_vehicle_id": validate_object_id(str(vehicle_id)) if vehicle_id else None,
                    "assigned_driver_id": None,
                    "updated_at": now,
                },
                "$unset": {"load_planning_exception": ""},
            },
        )

    selected_ids = set(assignments)
    excluded_ids = [
        validate_object_id(str(value))
        for value in plan.get("order_ids") or []
        if str(value) not in selected_ids
    ]
    if excluded_ids:
        await database[DELIVERY_COLLECTION].update_many(
            {
                "_id": {"$in": excluded_ids},
                "delivery_status": "pending",
                "load_planning_status": {"$in": ["consolidated", "failed", "planned", "vehicle_assigned"]},
            },
            {"$set": {
                "load_planning_status": "failed",
                "active_load_plan_id": plan_id,
                "active_load_id": None,
                "load_reservation_job_id": None,
                "assigned_vehicle_id": None,
                "assigned_driver_id": None,
                "load_planning_exception": "Excluded from the approved load candidate",
                "updated_at": now,
            }},
        )


PLANNING_INPUT_FIELDS = frozenset({
    "parcel_weight", "parcel_volume", "load_profile", "drop_latitude", "drop_longitude",
    "zone_id", "priority", "delivery_date", "delivery_period", "scheduled_date",
})


def planning_change_requires_revision(existing: dict[str, Any], updates: dict[str, Any]) -> bool:
    for key in PLANNING_INPUT_FIELDS & updates.keys():
        if updates.get(key) != existing.get(key):
            return True
    return False


async def invalidate_load_plan_for_order(existing: dict[str, Any], reason: str) -> None:
    planning_status = existing.get("load_planning_status") or "unplanned"
    if planning_status == "reserved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancel the running load optimization job before editing this parcel")
    if planning_status == "routed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancel the linked route before editing this parcel")
    database = _database()
    now = utc_now()
    consolidation_id = existing.get("active_consolidation_id")
    if consolidation_id:
        await database[PARCEL_CONSOLIDATIONS_COLLECTION].update_one(
            {"consolidation_id": consolidation_id, "status": {"$in": ["active", "planning", "planned", "approved"]}},
            {"$set": {"status": "superseded", "superseded_reason": reason, "source_changed": True, "updated_at": now}},
        )
    plan_id = existing.get("active_load_plan_id")
    if not plan_id:
        return
    await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].update_one(
        {"plan_id": plan_id, "status": {"$in": ["review_required", "approved"]}},
        {"$set": {
            "status": "superseded", "superseded_at": now, "superseded_reason": reason,
            "source_changed": True, "updated_at": now,
        }},
    )
    await database[DELIVERY_COLLECTION].update_many(
        {"active_load_plan_id": plan_id, "load_planning_status": {"$in": ["planned", "vehicle_assigned"]}},
        {"$set": {
            "load_planning_status": "unplanned", "active_load_plan_id": None, "active_load_id": None,
            "load_reservation_job_id": None, "assigned_vehicle_id": None, "updated_at": now,
        }},
    )


def _database():
    database = get_database()
    if database is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return database


def _batch_key(delivery_date: str, delivery_period: str) -> str:
    return f"colombo_central_branch:{delivery_date}:{delivery_period}"


async def get_batch_eligibility(delivery_date: str, delivery_period: str) -> dict[str, Any]:
    database = _database()
    rows = await database[DELIVERY_COLLECTION].find({
        "delivery_date": delivery_date,
        "delivery_period": delivery_period,
    }).sort("created_at", 1).to_list(length=5000)
    result = assess_batch_orders([safe_delivery_document(row) or {} for row in rows], delivery_date, delivery_period)
    demand_context: dict[str, Any] = {"available": False, "required_vehicle_shifts": None, "high_demand_zones": []}
    zones = sorted({str(row.get("zone_id")) for row in rows if row.get("zone_id")})
    if zones:
        from app.models.demand_model import FLEET_RECOMMENDATION_COLLECTION
        from app.services.demand_forecasting_service import get_active_run_id

        active_run_id = await get_active_run_id()
        if active_run_id is not None:
            day_start = datetime.fromisoformat(delivery_date).replace(tzinfo=timezone.utc)
            recommendations = await database[FLEET_RECOMMENDATION_COLLECTION].find({
                "model_run_id": active_run_id,
                "zone_id": {"$in": zones},
                "forecast_date": {"$gte": day_start, "$lt": day_start + timedelta(days=1)},
            }).to_list(length=100)
            demand_context = {
                "available": bool(recommendations),
                "required_vehicle_shifts": sum(int(item.get("estimated_required_vehicles") or 0) for item in recommendations),
                "high_demand_zones": [str(item.get("zone_id")) for item in recommendations if item.get("demand_level") in {"high", "very_high"}],
                "model_run_id": str(active_run_id),
            }
    return {
        "batch_key": _batch_key(delivery_date, delivery_period),
        "delivery_date": delivery_date,
        "delivery_period": delivery_period,
        "eligible_count": len(result["eligible_orders"]),
        "exception_count": len(result["exceptions"]),
        "excluded_count": len(result["excluded_orders"]),
        "demand_context": demand_context,
        **result,
    }


async def get_batch_consolidation(delivery_date: str, delivery_period: str) -> dict[str, Any]:
    database = _database()
    rows = await database[DELIVERY_COLLECTION].find({
        "delivery_date": delivery_date,
        "delivery_period": delivery_period,
    }).sort("created_at", 1).to_list(length=5000)
    result = assess_batch_orders(
        [safe_delivery_document(row) or {} for row in rows],
        delivery_date,
        delivery_period,
        allowed_planning_statuses={"unplanned", "failed", "consolidated"},
    )
    eligibility = await get_batch_eligibility(delivery_date, delivery_period)
    from app.load_optimization.engine import consolidate_batch

    snapshot = consolidate_batch(result["eligible_orders"])
    return {
        "batch_key": eligibility["batch_key"],
        "delivery_date": delivery_date,
        "delivery_period": delivery_period,
        "eligible_count": len(result["eligible_orders"]),
        "exception_count": len(result["exceptions"]),
        "excluded_count": len(result["excluded_orders"]),
        "exceptions": result["exceptions"],
        "excluded_orders": result["excluded_orders"],
        "demand_context": eligibility["demand_context"],
        **snapshot,
    }


async def get_parcel_consolidation(consolidation_id: str) -> dict[str, Any] | None:
    return safe_load_document(await _database()[PARCEL_CONSOLIDATIONS_COLLECTION].find_one({
        "consolidation_id": consolidation_id,
    }))


async def get_consolidation_planning_state(consolidation_id: str) -> dict[str, Any] | None:
    database = _database()
    consolidation = await database[PARCEL_CONSOLIDATIONS_COLLECTION].find_one({
        "consolidation_id": consolidation_id,
        "status": {"$nin": ["superseded", "cancelled"]},
    })
    if consolidation is None:
        return None

    plan = None
    if consolidation.get("active_plan_id"):
        plan = await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].find_one({
            "plan_id": consolidation["active_plan_id"],
            "status": {"$in": ["review_required", "approved"]},
        })
    if plan is None:
        plan = await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].find_one(
            {
                "consolidation_id": consolidation_id,
                "status": {"$in": ["review_required", "approved"]},
            },
            sort=[("created_at", -1)],
        )

    job = None
    if consolidation.get("active_job_id"):
        job = await database[LOAD_OPTIMIZATION_JOBS_COLLECTION].find_one({
            "job_id": consolidation["active_job_id"],
        })
    if job is None and plan is None:
        job = await database[LOAD_OPTIMIZATION_JOBS_COLLECTION].find_one(
            {"consolidation_id": consolidation_id},
            sort=[("created_at", -1)],
        )

    state = candidate_generation_state(job=job, plan=plan)
    return {
        "consolidation": safe_load_document(consolidation),
        "job": safe_load_document(job),
        "plan": safe_load_document(plan),
        **state,
    }


async def list_parcel_consolidations(
    *,
    delivery_date: str | None = None,
    delivery_period: str | None = None,
    status_filter: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if delivery_date:
        query["delivery_date"] = delivery_date
    if delivery_period:
        query["delivery_period"] = delivery_period
    if status_filter:
        query["status"] = status_filter
    if search:
        query["consolidation_id"] = {"$regex": search.strip(), "$options": "i"}
    rows = await _database()[PARCEL_CONSOLIDATIONS_COLLECTION].find(query).sort("created_at", -1).to_list(length=200)
    return [safe_load_document(row) or {} for row in rows]


async def create_parcel_consolidation(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    database = _database()
    delivery_date = str(payload["delivery_date"])
    delivery_period = str(payload["delivery_period"])
    rows = await database[DELIVERY_COLLECTION].find({
        "delivery_date": delivery_date,
        "delivery_period": delivery_period,
    }).sort("created_at", 1).to_list(length=5000)
    assessed = assess_batch_orders(
        [safe_delivery_document(row) or {} for row in rows],
        delivery_date,
        delivery_period,
        allowed_planning_statuses={"unplanned", "failed", "consolidated"},
    )
    orders = assessed["eligible_orders"]
    if not orders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "No eligible parcels are available for consolidation", "exceptions": assessed["exceptions"]},
        )
    source_fingerprint = build_batch_fingerprint(
        orders,
        delivery_date,
        delivery_period,
        seed=int(payload.get("seed", 17)),
    )
    existing = await database[PARCEL_CONSOLIDATIONS_COLLECTION].find_one({
        "source_fingerprint": source_fingerprint,
        "status": {"$in": ["active", "planning", "planned", "approved", "routed"]},
    })
    if existing is not None:
        return {"reused": True, "consolidation": safe_load_document(existing), "exceptions": assessed["exceptions"]}

    from app.load_optimization.engine import consolidate_batch

    snapshot = consolidate_batch(orders)
    batch_key = _batch_key(delivery_date, delivery_period)
    counter = await database[LOAD_SEQUENCE_COUNTERS_COLLECTION].find_one_and_update(
        {"_id": f"consolidation:{batch_key}"},
        {"$inc": {"sequence": 1}, "$set": {"updated_at": utc_now()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    sequence = int(counter.get("sequence", 1))
    consolidation_id = build_consolidation_id(delivery_date, delivery_period, sequence)
    document = build_consolidation_document(
        consolidation_id=consolidation_id,
        sequence=sequence,
        orders=orders,
        snapshot=snapshot,
        delivery_date=delivery_date,
        delivery_period=delivery_period,
        source_fingerprint=source_fingerprint,
        created_by=str(current_user["id"]),
    )
    document["exceptions"] = assessed["exceptions"]
    document["excluded_orders"] = assessed["excluded_orders"]
    try:
        await database[PARCEL_CONSOLIDATIONS_COLLECTION].insert_one(document)
    except DuplicateKeyError:
        concurrent = await database[PARCEL_CONSOLIDATIONS_COLLECTION].find_one({"source_fingerprint": source_fingerprint})
        if concurrent is not None:
            return {"reused": True, "consolidation": safe_load_document(concurrent), "exceptions": assessed["exceptions"]}
        raise

    parcel_object_ids = [validate_object_id(order["id"]) for order in orders]
    update_result = await database[DELIVERY_COLLECTION].update_many(
        {
            "_id": {"$in": parcel_object_ids},
            "delivery_status": "pending",
            "load_planning_status": {"$in": ["unplanned", "failed", "consolidated"]},
        },
        {"$set": {
            "load_planning_status": "consolidated",
            "active_consolidation_id": consolidation_id,
            "load_planning_exception": None,
            "updated_at": utc_now(),
        }},
    )
    if update_result.matched_count != len(parcel_object_ids):
        await database[PARCEL_CONSOLIDATIONS_COLLECTION].update_one(
            {"consolidation_id": consolidation_id},
            {"$set": {"status": "cancelled", "cancel_reason": "Parcel state changed concurrently", "updated_at": utc_now()}},
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="One or more parcels changed while consolidation was being created")
    await database[PARCEL_CONSOLIDATIONS_COLLECTION].update_many(
        {
            "batch_key": batch_key,
            "consolidation_id": {"$ne": consolidation_id},
            "status": "active",
        },
        {"$set": {"status": "superseded", "superseded_by": consolidation_id, "updated_at": utc_now()}},
    )
    return {"reused": False, "consolidation": safe_load_document(document), "exceptions": assessed["exceptions"]}


async def get_vehicle_type_catalog() -> dict[str, Any]:
    vehicles = await _database()[VEHICLE_COLLECTION].find(
        {}, {"status": 1, "load_profile": 1},
    ).to_list(length=5000)
    items = build_vehicle_type_catalog_view(DEFAULT_VEHICLE_TYPE_CATALOG, vehicles)
    return {"items": items, "total": len(items)}


async def create_optimization_job(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    database = _database()
    delivery_date = str(payload["delivery_date"])
    delivery_period = str(payload["delivery_period"])
    consolidation_id = payload.get("consolidation_id")
    query: dict[str, Any] = {"delivery_date": delivery_date, "delivery_period": delivery_period}
    consolidation = None
    if consolidation_id:
        consolidation = await database[PARCEL_CONSOLIDATIONS_COLLECTION].find_one({
            "consolidation_id": consolidation_id,
            "delivery_date": delivery_date,
            "delivery_period": delivery_period,
            "status": {"$in": ["active", "planning", "planned", "approved"]},
        })
        if consolidation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active parcel consolidation not found")
        planning_state = await get_consolidation_planning_state(str(consolidation_id))
        if planning_state and planning_state.get("plan"):
            return {
                "reused": True,
                "job": planning_state.get("job"),
                "plan": planning_state["plan"],
                "exceptions": consolidation.get("exceptions") or [],
            }
        if planning_state and str((planning_state.get("job") or {}).get("status")) in {"queued", "running"}:
            return {
                "reused": True,
                "job": planning_state["job"],
                "plan": None,
                "exceptions": consolidation.get("exceptions") or [],
            }
        query["_id"] = {"$in": [validate_object_id(value) for value in consolidation.get("parcel_ids", [])]}
    requested_ids = payload.get("order_ids") or []
    if requested_ids and consolidation_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Use either consolidation_id or order_ids, not both")
    if requested_ids:
        try:
            query["_id"] = {"$in": [validate_object_id(value) for value in requested_ids]}
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more parcel IDs are invalid") from exc

    raw_orders = await database[DELIVERY_COLLECTION].find(query).sort("created_at", 1).to_list(length=5000)
    assessed = assess_batch_orders(
        [safe_delivery_document(row) or {} for row in raw_orders],
        delivery_date,
        delivery_period,
        allowed_planning_statuses={"consolidated"} if consolidation_id else None,
        consolidation_id=str(consolidation_id) if consolidation_id else None,
    )
    eligible = assessed["eligible_orders"]
    if not eligible:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "No eligible parcels are available for this planning batch", "exceptions": assessed["exceptions"]},
        )

    job = build_optimization_job_document(
        orders=eligible,
        delivery_date=delivery_date,
        delivery_period=delivery_period,
        seed=int(payload.get("seed", 17)),
        created_by=str(current_user["id"]),
        consolidation_id=str(consolidation_id) if consolidation_id else None,
    )
    matching_plan = await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].find_one({
        "input_fingerprint": job["input_fingerprint"],
        "status": {"$in": ["approved", "review_required"]},
    })
    if matching_plan:
        return {"reused": True, "job": None, "plan": safe_load_document(matching_plan), "exceptions": assessed["exceptions"]}
    matching_job = await database[LOAD_OPTIMIZATION_JOBS_COLLECTION].find_one({
        "input_fingerprint": job["input_fingerprint"],
        "status": {"$in": ["queued", "running"]},
    })
    if matching_job:
        return {"reused": True, "job": safe_load_document(matching_job), "plan": None, "exceptions": assessed["exceptions"]}

    order_object_ids = [validate_object_id(item["id"]) for item in eligible]
    reservation_result = await database[DELIVERY_COLLECTION].update_many(
        {
            "_id": {"$in": order_object_ids},
            "delivery_status": "pending",
            "load_planning_status": {"$in": ["consolidated"] if consolidation_id else ["unplanned", "failed"]},
            **({"active_consolidation_id": consolidation_id} if consolidation_id else {}),
        },
        {"$set": {
            "load_planning_status": "reserved",
            "load_reservation_job_id": job["job_id"],
            "updated_at": utc_now(),
        }},
    )
    if reservation_result.modified_count != len(order_object_ids):
        await database[DELIVERY_COLLECTION].update_many(
            {"load_reservation_job_id": job["job_id"]},
            {"$set": {"load_planning_status": "consolidated" if consolidation_id else "unplanned", "load_reservation_job_id": None, "updated_at": utc_now()}},
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="One or more parcels were reserved by another planning job")

    try:
        await database[LOAD_OPTIMIZATION_JOBS_COLLECTION].insert_one(job)
    except (DuplicateKeyError, PyMongoError) as exc:
        await database[DELIVERY_COLLECTION].update_many(
            {"load_reservation_job_id": job["job_id"]},
            {"$set": {"load_planning_status": "consolidated" if consolidation_id else "unplanned", "load_reservation_job_id": None, "updated_at": utc_now()}},
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Unable to queue load optimization") from exc
    if consolidation_id:
        await database[PARCEL_CONSOLIDATIONS_COLLECTION].update_one(
            {"consolidation_id": consolidation_id, "status": "active"},
            {"$set": {"status": "planning", "active_job_id": job["job_id"], "updated_at": utc_now()}},
        )
    return {"reused": False, "job": safe_load_document(job), "plan": None, "exceptions": assessed["exceptions"]}


async def get_optimization_job(job_id: str) -> dict[str, Any] | None:
    return safe_load_document(await _database()[LOAD_OPTIMIZATION_JOBS_COLLECTION].find_one({"job_id": job_id}))


async def cancel_optimization_job(job_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    database = _database()
    now = utc_now()
    job = await database[LOAD_OPTIMIZATION_JOBS_COLLECTION].find_one_and_update(
        {"job_id": job_id, "status": {"$in": ["queued", "running"]}},
        {"$set": {
            "status": "cancelled",
            "stage": "cancelled",
            "cancel_requested_at": now,
            "cancelled_by": str(current_user["id"]),
            "updated_at": now,
        }},
        return_document=ReturnDocument.AFTER,
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only queued or running jobs can be cancelled")
    restore_status = "consolidated" if job.get("consolidation_id") else "unplanned"
    await database[DELIVERY_COLLECTION].update_many(
        {"load_reservation_job_id": job_id, "load_planning_status": "reserved"},
        {"$set": {"load_planning_status": restore_status, "load_reservation_job_id": None, "updated_at": now}},
    )
    if job.get("consolidation_id"):
        await database[PARCEL_CONSOLIDATIONS_COLLECTION].update_one(
            {"consolidation_id": job["consolidation_id"], "active_job_id": job_id},
            {"$set": {"status": "active", "active_job_id": None, "updated_at": now}},
        )
    return safe_load_document(job) or {}


async def list_load_plans(
    *, delivery_date: str | None = None, delivery_period: str | None = None, status_filter: str | None = None,
    consolidation_id: str | None = None,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if delivery_date:
        query["delivery_date"] = delivery_date
    if delivery_period:
        query["delivery_period"] = delivery_period
    if status_filter:
        query["status"] = status_filter
    if consolidation_id:
        query["consolidation_id"] = consolidation_id
    rows = await _database()[LOAD_OPTIMIZATION_PLANS_COLLECTION].find(query).sort("created_at", -1).to_list(length=200)
    return [safe_load_document(row) or {} for row in rows]


async def get_load_plan(plan_id: str) -> dict[str, Any] | None:
    return safe_load_document(await _database()[LOAD_OPTIMIZATION_PLANS_COLLECTION].find_one({"plan_id": plan_id}))


async def approve_load_plan(plan_id: str, option_id: str | None, current_user: dict[str, Any]) -> dict[str, Any]:
    database = _database()
    plan = await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].find_one({"plan_id": plan_id})
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load plan not found")
    try:
        validate_plan_transition(str(plan.get("status")), "approved")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    options = plan.get("pareto_options") or []
    selected = next((item for item in options if item.get("option_id") == option_id), None) if option_id else plan.get("selected_option")
    if selected is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A valid Pareto option must be selected")
    now = utc_now()
    await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].update_one(
        {"plan_id": plan_id, "status": "review_required"},
        {"$set": {
            "status": "approved",
            "selected_option": selected,
            "approved_at": now,
            "approved_by": str(current_user["id"]),
            "updated_at": now,
        }},
    )
    if plan.get("consolidation_id"):
        await database[PARCEL_CONSOLIDATIONS_COLLECTION].update_one(
            {"consolidation_id": plan["consolidation_id"]},
            {"$set": {"status": "approved", "active_plan_id": plan_id, "updated_at": now}},
        )
    await synchronize_approved_plan_deliveries({
        **plan,
        "status": "approved",
        "selected_option": selected,
    })
    return await get_load_plan(plan_id) or {}


async def get_vehicle_suggestions(plan_id: str) -> dict[str, Any]:
    plan = await get_load_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load plan not found")
    option = plan.get("selected_option") or {}
    loads = option.get("loads") or []
    vehicles = await _database()[VEHICLE_COLLECTION].find({"status": "active"}).sort("registration_number", 1).to_list(length=1000)
    external_assignments = await _database()[LOAD_OPTIMIZATION_PLANS_COLLECTION].find(
        {
            "status": "approved",
            "plan_id": {"$ne": plan_id},
            "delivery_date": plan.get("delivery_date"),
            "delivery_period": plan.get("delivery_period"),
        },
        {"selected_option.loads.assigned_vehicle_id": 1},
    ).to_list(length=500)
    externally_reserved = {
        str(load.get("assigned_vehicle_id"))
        for other_plan in external_assignments
        for load in ((other_plan.get("selected_option") or {}).get("loads") or [])
        if load.get("assigned_vehicle_id")
    }
    suggestions: list[dict[str, Any]] = []
    from app.services.fleet_intelligence_service import validate_vehicle_for_planning
    readiness_cache: dict[str, dict[str, Any]] = {}

    for virtual_load in loads:
        matches = []
        for raw_vehicle in vehicles:
            vehicle = safe_vehicle_document(raw_vehicle) or {}
            vehicle_id = str(vehicle.get("id") or "")
            reserved_by_other_load = any(
                other.get("load_id") != virtual_load.get("load_id")
                and str(other.get("assigned_vehicle_id") or "") == vehicle_id
                for other in loads
            )
            if vehicle_id in externally_reserved or reserved_by_other_load:
                continue
            result = vehicle_supports_virtual_load(vehicle, virtual_load)
            if result["eligible"]:
                if vehicle_id not in readiness_cache:
                    readiness_cache[vehicle_id] = await validate_vehicle_for_planning(vehicle_id)
                readiness = readiness_cache[vehicle_id]
                if readiness.get("eligible"):
                    matches.append({
                        "vehicle": vehicle,
                        "compatibility": result,
                        "readiness": public_readiness_summary(readiness),
                    })
        suggestions.append({"load_id": virtual_load.get("load_id"), "matches": matches})
    return {"plan_id": plan_id, "suggestions": suggestions}


async def assign_physical_vehicle(plan_id: str, load_id: str, vehicle_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    database = _database()
    plan = await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].find_one({"plan_id": plan_id, "status": "approved"})
    if plan is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only an approved load plan can receive vehicle assignments")
    option = plan.get("selected_option") or {}
    loads = option.get("loads") or []
    load = next((item for item in loads if item.get("load_id") == load_id), None)
    if load is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Virtual load not found")
    vehicle_object_id = validate_object_id(vehicle_id)
    raw_vehicle = await database[VEHICLE_COLLECTION].find_one({"_id": vehicle_object_id})
    if raw_vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    compatibility = vehicle_supports_virtual_load(safe_vehicle_document(raw_vehicle) or {}, load)
    if not compatibility["eligible"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"message": "Vehicle is not compatible with this load", **compatibility})
    if await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].find_one({
        "status": "approved", "selected_option.loads.assigned_vehicle_id": str(vehicle_id), "plan_id": {"$ne": plan_id},
        "delivery_date": plan["delivery_date"], "delivery_period": plan["delivery_period"],
    }):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vehicle is already assigned to another load in this operating window")
    if any(
        other.get("load_id") != load_id
        and str(other.get("assigned_vehicle_id") or "") == str(vehicle_id)
        for other in loads
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vehicle is already assigned to another load in this plan")

    now = utc_now()
    physical_profile = raw_vehicle.get("load_profile") or {}
    result = await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].update_one(
        {"plan_id": plan_id, "status": "approved", "selected_option.loads.load_id": load_id},
        {"$set": {
            "selected_option.loads.$.assigned_vehicle_id": str(vehicle_id),
            "selected_option.loads.$.assigned_at": now,
            "selected_option.loads.$.assigned_by": str(current_user["id"]),
            "selected_option.loads.$.assigned_cargo_length_cm": physical_profile.get("cargo_length_cm"),
            "selected_option.loads.$.assigned_cargo_width_cm": physical_profile.get("cargo_width_cm"),
            "selected_option.loads.$.assigned_cargo_height_cm": physical_profile.get("cargo_height_cm"),
            "updated_at": now,
        }},
    )
    if result.modified_count != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vehicle assignment changed concurrently")
    updated_plan = await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].find_one({"plan_id": plan_id})
    if updated_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load plan not found")
    await synchronize_approved_plan_deliveries(updated_plan)
    return await get_load_plan(plan_id) or {}


async def release_load_plan(plan_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    database = _database()
    plan = await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].find_one({"plan_id": plan_id})
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load plan not found")
    if plan.get("consolidation_id"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Generated consolidation candidates are immutable and cannot be released",
        )
    if plan.get("status") not in {"review_required", "approved"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This load plan cannot be released")
    now = utc_now()
    await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].update_one(
        {"plan_id": plan_id, "status": plan["status"]},
        {"$set": {"status": "superseded", "released_at": now, "released_by": str(current_user["id"]), "updated_at": now}},
    )
    restore_status = "consolidated" if plan.get("consolidation_id") else "unplanned"
    await database[DELIVERY_COLLECTION].update_many(
        {"active_load_plan_id": plan_id, "load_planning_status": {"$in": ["planned", "vehicle_assigned"]}},
        {"$set": {
            "load_planning_status": restore_status, "active_load_plan_id": None, "active_load_id": None,
            "load_reservation_job_id": None, "assigned_vehicle_id": None, "updated_at": now,
        }},
    )
    if plan.get("consolidation_id"):
        await database[PARCEL_CONSOLIDATIONS_COLLECTION].update_one(
            {"consolidation_id": plan["consolidation_id"]},
            {"$set": {"status": "active", "active_plan_id": None, "updated_at": now}},
        )
    return await get_load_plan(plan_id) or {}


async def export_load_plan_csv(plan_id: str) -> str:
    plan = await get_load_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load plan not found")
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["plan_id", "revision", "load_id", "vehicle_type", "assigned_vehicle_id", "loading_sequence", "parcel_id", "x_cm", "y_cm", "z_cm"])
    for load in (plan.get("selected_option") or {}).get("loads", []):
        placements = {str(item.get("parcel_id")): item for item in load.get("placements", [])}
        for sequence, parcel_id in enumerate(load.get("loading_sequence", []), start=1):
            placement = placements.get(str(parcel_id), {})
            writer.writerow([
                plan_id, plan.get("revision"), load.get("load_id"), load.get("vehicle_type_code"),
                load.get("assigned_vehicle_id"), sequence, parcel_id, placement.get("x_cm"),
                placement.get("y_cm"), placement.get("z_cm"),
            ])
    return output.getvalue()


async def claim_next_job(worker_id: str, lease_seconds: int = 120) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    job = await _database()[LOAD_OPTIMIZATION_JOBS_COLLECTION].find_one_and_update(
        {
            "status": {"$in": ["queued", "running"]},
            "$or": [{"status": "queued"}, {"lease_expires_at": {"$lt": now}}],
        },
        {"$set": {
            "status": "running", "stage": "loading_inputs", "lease_owner": worker_id,
            "lease_expires_at": now + timedelta(seconds=lease_seconds), "heartbeat_at": now, "updated_at": now,
        }, "$inc": {"attempt_count": 1}},
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )
    return safe_load_document(job)


async def heartbeat_job(job_id: str, worker_id: str, stage: str, progress_percent: int, lease_seconds: int = 120) -> bool:
    now = datetime.now(timezone.utc)
    result = await _database()[LOAD_OPTIMIZATION_JOBS_COLLECTION].update_one(
        {"job_id": job_id, "status": "running", "lease_owner": worker_id},
        {"$set": {
            "stage": stage, "progress_percent": max(0, min(int(progress_percent), 99)),
            "heartbeat_at": now, "lease_expires_at": now + timedelta(seconds=lease_seconds), "updated_at": now,
        }},
    )
    return result.modified_count == 1


async def complete_job(job_id: str, worker_id: str, result: dict[str, Any]) -> dict[str, Any]:
    database = _database()
    job = await database[LOAD_OPTIMIZATION_JOBS_COLLECTION].find_one({"job_id": job_id, "status": "running", "lease_owner": worker_id})
    if job is None:
        raise RuntimeError("Worker no longer owns this load optimization job")
    latest = await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].find_one({"batch_key": job["batch_key"]}, sort=[("revision", -1)])
    revision = int((latest or {}).get("revision", 0)) + 1
    now = utc_now()
    plan_id = f"LOADPLAN-{now:%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"
    options = result.get("pareto_options") or []
    selected = result.get("selected_option") or (options[0] if options else None)
    plan = {
        "plan_id": plan_id, "job_id": job_id, "batch_key": job["batch_key"], "revision": revision,
        "delivery_date": job["delivery_date"], "delivery_period": job["delivery_period"],
        "consolidation_id": job.get("consolidation_id"),
        "input_fingerprint": job["input_fingerprint"], "seed": job["seed"], "status": "review_required",
        "order_ids": job["order_ids"], "regions": result.get("regions", []), "exceptions": result.get("exceptions", []),
        "pareto_options": options, "selected_option": selected, "engine": result.get("engine", {}),
        "created_at": now, "updated_at": now,
    }
    await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].insert_one(plan)
    if job.get("consolidation_id"):
        await database[PARCEL_CONSOLIDATIONS_COLLECTION].update_one(
            {"consolidation_id": job["consolidation_id"]},
            {"$set": {"status": "planned", "active_plan_id": plan_id, "updated_at": now}},
        )
    parcel_load_map: dict[str, str] = {}
    for load in (selected or {}).get("loads", []):
        for parcel_id in load.get("parcel_ids", []):
            parcel_load_map[str(parcel_id)] = str(load["load_id"])
    for parcel_id, load_id in parcel_load_map.items():
        await database[DELIVERY_COLLECTION].update_one(
            {"_id": validate_object_id(parcel_id), "load_reservation_job_id": job_id, "load_planning_status": "reserved"},
            {"$set": {
                "load_planning_status": "planned", "active_load_plan_id": plan_id, "active_load_id": load_id,
                "load_reservation_job_id": None, "updated_at": now,
            }},
        )
    unassigned_count = await database[DELIVERY_COLLECTION].count_documents({
        "load_reservation_job_id": job_id,
        "load_planning_status": "reserved",
    })
    if unassigned_count:
        await database[DELIVERY_COLLECTION].update_many(
            {"load_reservation_job_id": job_id, "load_planning_status": "reserved"},
            {"$set": {
                "load_planning_status": "failed",
                "load_planning_exception": "No safe compatible virtual load was available",
                "load_reservation_job_id": None,
                "updated_at": now,
            }},
        )
    await database[LOAD_OPTIMIZATION_JOBS_COLLECTION].update_one(
        {"job_id": job_id, "lease_owner": worker_id},
        {"$set": {
            "status": "completed", "stage": "review_required", "progress_percent": 100,
            "plan_id": plan_id, "unassigned_parcel_count": unassigned_count,
            "completed_at": now, "lease_expires_at": None, "updated_at": now,
        }},
    )
    return safe_load_document(plan) or {}


async def fail_job(job_id: str, worker_id: str, message: str) -> None:
    database = _database()
    now = utc_now()
    job = await database[LOAD_OPTIMIZATION_JOBS_COLLECTION].find_one({"job_id": job_id})
    await database[LOAD_OPTIMIZATION_JOBS_COLLECTION].update_one(
        {"job_id": job_id, "lease_owner": worker_id},
        {"$set": {"status": "failed", "stage": "failed", "error": str(message)[:1000], "updated_at": now, "lease_expires_at": None}},
    )
    restore_status = "consolidated" if (job or {}).get("consolidation_id") else "failed"
    await database[DELIVERY_COLLECTION].update_many(
        {"load_reservation_job_id": job_id, "load_planning_status": "reserved"},
        {"$set": {"load_planning_status": restore_status, "load_reservation_job_id": None, "updated_at": now}},
    )
    if (job or {}).get("consolidation_id"):
        await database[PARCEL_CONSOLIDATIONS_COLLECTION].update_one(
            {"consolidation_id": job["consolidation_id"]},
            {"$set": {"status": "active", "active_job_id": None, "last_error": str(message)[:1000], "updated_at": now}},
        )
