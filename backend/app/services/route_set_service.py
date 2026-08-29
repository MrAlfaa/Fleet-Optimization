from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.database import get_database
from app.models.load_optimization_model import LOAD_OPTIMIZATION_PLANS_COLLECTION, PARCEL_CONSOLIDATIONS_COLLECTION
from app.models.route_model import ROUTE_PLAN_COLLECTION, ROUTE_SET_COLLECTION, safe_route_document
from app.models.user_model import utc_now
from app.services.driver_device_service import validate_driver_for_assignment
from app.services.fleet_intelligence_service import validate_vehicle_assignment
from app.services.route_optimizer_service import cancel_route, dispatch_route, get_route_plan, optimize_route
from app.utils.object_id import validate_object_id


def validate_route_set_for_approval(route_set: dict[str, Any], routes: list[dict[str, Any]]) -> None:
    if route_set.get("status") != "review_required":
        raise ValueError("Only a route set awaiting review can be approved")
    expected = int(route_set.get("expected_route_count") or len(route_set.get("route_ids") or []))
    if expected < 1 or len(routes) != expected:
        raise ValueError("A route must exist for every approved load")
    if any(route.get("status") != "optimized" for route in routes):
        raise ValueError("Every route must be optimized before route-set approval")


def validate_route_set_for_dispatch(route_set: dict[str, Any], routes: list[dict[str, Any]]) -> None:
    if route_set.get("status") not in {"approved", "dispatching"}:
        raise ValueError("Approve the route set before dispatch")
    expected = int(route_set.get("expected_route_count") or len(route_set.get("route_ids") or []))
    if expected < 1 or len(routes) != expected:
        raise ValueError("Every approved route must be available before dispatch")
    for route in routes:
        if route.get("status") not in {"approved", "dispatched"}:
            raise ValueError("Every route must be approved before dispatch")
        if not route.get("vehicle_id"):
            raise ValueError("Every route requires a vehicle before dispatch")
        if not route.get("driver_id"):
            raise ValueError("Every route requires a driver before dispatch")
    driver_ids = [str(route["driver_id"]) for route in routes]
    if len(driver_ids) != len(set(driver_ids)):
        raise ValueError("A driver can be assigned to only one route in a route set")


def approved_load_delivery_ids(selected_option: dict[str, Any]) -> dict[str, list[str]]:
    exception_ids = {
        str(exception.get("parcel_id"))
        for exception in selected_option.get("exceptions") or []
        if exception.get("parcel_id")
    }
    by_load: dict[str, list[str]] = {}
    seen: set[str] = set()
    for load in selected_option.get("loads") or []:
        load_id = str(load.get("load_id") or "").strip()
        if not load_id:
            raise ValueError("Every approved load requires a load ID")
        parcel_ids = [str(value) for value in load.get("parcel_ids") or []]
        if not parcel_ids:
            raise ValueError(f"Approved load {load_id} has no deliverable parcels")
        if any(parcel_id in exception_ids for parcel_id in parcel_ids):
            raise ValueError("An exception parcel cannot be included in an approved load")
        if any(parcel_id in seen for parcel_id in parcel_ids):
            raise ValueError("A parcel cannot appear in more than one approved load")
        if len(parcel_ids) != len(set(parcel_ids)):
            raise ValueError("A parcel cannot appear more than once in an approved load")
        seen.update(parcel_ids)
        by_load[load_id] = parcel_ids
    return by_load


def _db():
    database = get_database()
    if database is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is unavailable")
    return database


async def get_route_set(route_set_id: str) -> dict[str, Any] | None:
    document = await _db()[ROUTE_SET_COLLECTION].find_one({"route_set_id": route_set_id})
    if document is None:
        return None
    result = safe_route_document(document) or {}
    routes = []
    for route_id in document.get("route_ids") or []:
        route = await get_route_plan(str(route_id))
        if route is not None:
            routes.append(route)
    result["routes"] = routes
    return result


async def create_route_set(load_plan_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    database = _db()
    existing = await database[ROUTE_SET_COLLECTION].find_one({"load_plan_id": load_plan_id})
    if existing is not None and existing.get("status") not in {"failed", "cancelled"}:
        return await get_route_set(str(existing["route_set_id"])) or {}

    plan = await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].find_one({"plan_id": load_plan_id, "status": "approved"})
    if plan is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approve a load candidate before generating routes")
    selected = plan.get("selected_option") or {}
    loads = selected.get("loads") or []
    if not loads:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The approved candidate has no vehicle loads")
    if any(not load.get("assigned_vehicle_id") for load in loads):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assign a compatible physical vehicle to every approved load")
    try:
        delivery_ids_by_load = approved_load_delivery_ids({
            **selected,
            "exceptions": selected.get("exceptions") or plan.get("exceptions") or [],
        })
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # Repairs plans approved before candidate-selection parcel rebinding was enforced.
    from app.services.load_optimization_service import synchronize_approved_plan_deliveries
    await synchronize_approved_plan_deliveries(plan)

    now = utc_now()
    route_set_id = str(existing["route_set_id"]) if existing else f"RSET-{now:%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
    document = {
        "route_set_id": route_set_id,
        "load_plan_id": load_plan_id,
        "option_id": selected.get("option_id"),
        "consolidation_id": plan.get("consolidation_id"),
        "delivery_date": plan.get("delivery_date"),
        "delivery_period": plan.get("delivery_period"),
        "expected_route_count": len(loads),
        "route_ids": [],
        "status": "generating",
        "created_by": str(current_user.get("id") or ""),
        "created_at": now,
        "updated_at": now,
    }
    if existing is not None:
        retry = await database[ROUTE_SET_COLLECTION].update_one(
            {"_id": existing["_id"], "status": {"$in": ["failed", "cancelled"]}},
            {"$set": {**document, "error": None, "last_error": None}},
        )
        if retry.modified_count != 1:
            concurrent = await database[ROUTE_SET_COLLECTION].find_one({"load_plan_id": load_plan_id})
            if concurrent is not None:
                return await get_route_set(str(concurrent["route_set_id"])) or {}
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Route generation state changed; refresh and retry")
    else:
        try:
            await database[ROUTE_SET_COLLECTION].insert_one(document)
        except DuplicateKeyError:
            concurrent = await database[ROUTE_SET_COLLECTION].find_one({"load_plan_id": load_plan_id})
            if concurrent is not None:
                return await get_route_set(str(concurrent["route_set_id"])) or {}
            raise

    created_route_ids: list[str] = []
    try:
        for index, load in enumerate(loads, start=1):
            optimized = await optimize_route(
                {
                    "route_name": f"{plan.get('consolidation_id') or load_plan_id} · Load {index}",
                    "vehicle_id": str(load["assigned_vehicle_id"]),
                    "driver_id": None,
                    "delivery_order_ids": delivery_ids_by_load[str(load["load_id"])],
                    "delivery_date": plan.get("delivery_date"),
                    "delivery_period": plan.get("delivery_period"),
                    "load_plan_id": load_plan_id,
                    "load_id": str(load["load_id"]),
                    "option_id": selected.get("option_id"),
                    "consolidation_id": plan.get("consolidation_id"),
                    "route_set_id": route_set_id,
                    "save_route": True,
                    "use_ml_cost": True,
                    "include_demand_context": True,
                    "include_maintenance_context": True,
                    "include_weather_context": True,
                },
                current_user,
            )
            created_route_ids.append(str(optimized["route_id"]))
            await database[ROUTE_SET_COLLECTION].update_one(
                {"route_set_id": route_set_id},
                {"$set": {"route_ids": created_route_ids, "updated_at": utc_now()}},
            )
    except Exception as exc:
        for route_id in created_route_ids:
            try:
                await cancel_route(route_id, current_user)
            except Exception:
                pass
        await database[ROUTE_SET_COLLECTION].update_one(
            {"route_set_id": route_set_id},
            {"$set": {"status": "failed", "error": str(exc)[:1000], "updated_at": utc_now()}},
        )
        raise

    await database[ROUTE_SET_COLLECTION].update_one(
        {"route_set_id": route_set_id},
        {"$set": {"status": "review_required", "route_ids": created_route_ids, "updated_at": utc_now()}},
    )
    await database[LOAD_OPTIMIZATION_PLANS_COLLECTION].update_one(
        {"plan_id": load_plan_id},
        {"$set": {"route_set_id": route_set_id, "updated_at": utc_now()}},
    )
    if plan.get("consolidation_id"):
        await database[PARCEL_CONSOLIDATIONS_COLLECTION].update_one(
            {"consolidation_id": plan["consolidation_id"]},
            {"$set": {"status": "planned", "active_route_set_id": route_set_id, "updated_at": utc_now()}},
        )
    return await get_route_set(route_set_id) or {}


async def approve_route_set(route_set_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    database = _db()
    result = await get_route_set(route_set_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route set not found")
    try:
        validate_route_set_for_approval(result, result.get("routes") or [])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    route_object_ids = [validate_object_id(value) for value in result["route_ids"]]
    now = utc_now()
    await database[ROUTE_PLAN_COLLECTION].update_many(
        {"_id": {"$in": route_object_ids}, "status": "optimized"},
        {"$set": {"status": "approved", "approved_at": now, "approved_by": str(current_user.get("id") or ""), "updated_at": now}},
    )
    await database[ROUTE_SET_COLLECTION].update_one(
        {"route_set_id": route_set_id, "status": "review_required"},
        {"$set": {"status": "approved", "approved_at": now, "approved_by": str(current_user.get("id") or ""), "updated_at": now}},
    )
    if result.get("consolidation_id"):
        await database[PARCEL_CONSOLIDATIONS_COLLECTION].update_one(
            {"consolidation_id": result["consolidation_id"]},
            {"$set": {"status": "routed", "updated_at": now}},
        )
    return await get_route_set(route_set_id) or {}


async def assign_route_driver(route_set_id: str, route_id: str, driver_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    del current_user
    database = _db()
    route_set = await database[ROUTE_SET_COLLECTION].find_one({"route_set_id": route_set_id, "status": "approved"})
    if route_set is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approve the route set before assigning drivers")
    if route_id not in [str(value) for value in route_set.get("route_ids") or []]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route is not part of this route set")
    await validate_driver_for_assignment(driver_id, route_id)
    conflicting_route = await database[ROUTE_PLAN_COLLECTION].find_one({
        "_id": {"$ne": validate_object_id(route_id)},
        "route_set_id": route_set_id,
        "driver_id": validate_object_id(driver_id),
        "status": "approved",
    })
    if conflicting_route is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This driver is already assigned to another route in this route set")
    result = await database[ROUTE_PLAN_COLLECTION].update_one(
        {"_id": validate_object_id(route_id), "route_set_id": route_set_id, "status": "approved"},
        {"$set": {"driver_id": validate_object_id(driver_id), "driver_assigned_at": utc_now(), "updated_at": utc_now()}},
    )
    if result.modified_count != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This driver assignment could not be saved")
    return await get_route_set(route_set_id) or {}


async def dispatch_route_set(route_set_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    database = _db()
    result = await get_route_set(route_set_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route set not found")
    try:
        validate_route_set_for_dispatch(result, result.get("routes") or [])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    for route in result.get("routes") or []:
        if route.get("status") == "dispatched":
            continue
        assignment = await validate_vehicle_assignment(str(route["vehicle_id"]), str(route["id"]), create_block_alert=True)
        if not assignment["eligible"]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="; ".join(assignment["blocking_reasons"]))
        await validate_driver_for_assignment(str(route["driver_id"]), str(route["id"]))

    await database[ROUTE_SET_COLLECTION].update_one(
        {"route_set_id": route_set_id, "status": {"$in": ["approved", "dispatching"]}},
        {"$set": {"status": "dispatching", "updated_at": utc_now()}},
    )
    try:
        for route in result.get("routes") or []:
            if route.get("status") != "dispatched":
                await dispatch_route(str(route["id"]), {}, current_user)
    except Exception as exc:
        await database[ROUTE_SET_COLLECTION].update_one(
            {"route_set_id": route_set_id},
            {"$set": {"status": "dispatching", "last_error": str(exc)[:1000], "updated_at": utc_now()}},
        )
        raise
    await database[ROUTE_SET_COLLECTION].update_one(
        {"route_set_id": route_set_id},
        {"$set": {"status": "dispatched", "dispatched_at": utc_now(), "last_error": None, "updated_at": utc_now()}},
    )
    return await get_route_set(route_set_id) or {}
