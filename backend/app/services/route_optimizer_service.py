from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.delivery_model import DELIVERY_COLLECTION
from app.models.route_model import (
    ROUTE_PLAN_COLLECTION,
    ROUTE_SEGMENT_COLLECTION,
    build_route_plan_document,
    build_route_segment_document,
    safe_route_document,
)
from app.models.user_model import utc_now
from app.models.vehicle_model import VEHICLE_COLLECTION
from app.services.alert_service import create_alert
from app.services.delivery_service import get_raw_delivery_order_by_id, update_delivery_order
from app.services.route_prediction_service import calculate_segment_cost
from app.services.vehicle_service import get_vehicle_by_id
from app.utils.geo_utils import haversine_distance_km
from app.utils.object_id import serialize_mongo_list, validate_object_id
from app.utils.pagination import build_pagination_response, calculate_skip, normalize_pagination
from app.utils.route_utils import format_optimized_stop_order


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db


def get_route_plan_collection():
    return _db()[ROUTE_PLAN_COLLECTION]


def get_route_segment_collection():
    return _db()[ROUTE_SEGMENT_COLLECTION]


async def build_points_from_orders_or_stops(request_data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[Any]]:
    points = [
        {
            "type": "depot",
            "order_id": None,
            "order_code": "DEPOT",
            "latitude": request_data["depot_latitude"],
            "longitude": request_data["depot_longitude"],
            "zone_id": None,
            "priority": None,
        }
    ]
    order_ids: list[Any] = []
    for order_id in request_data.get("delivery_order_ids") or []:
        order = await get_raw_delivery_order_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Delivery order not found: {order_id}")
        order_ids.append(order["_id"])
        points.append(
            {
                "type": "delivery",
                "order_id": str(order["_id"]),
                "order_code": order["order_code"],
                "latitude": order["drop_latitude"],
                "longitude": order["drop_longitude"],
                "zone_id": order.get("zone_id"),
                "priority": order.get("priority"),
            }
        )

    for stop in request_data.get("delivery_stops") or []:
        points.append(
            {
                "type": "delivery",
                "order_id": None,
                "order_code": stop.get("order_code"),
                "latitude": stop["drop_latitude"],
                "longitude": stop["drop_longitude"],
                "zone_id": stop.get("zone_id"),
                "priority": stop.get("priority"),
            }
        )
    if len(points) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one delivery stop is required")
    return points, order_ids


async def _get_demand_context(points: list[dict[str, Any]]) -> dict[str, Any]:
    zones = sorted({point.get("zone_id") for point in points if point.get("zone_id")})
    if not zones:
        return {"zones": [], "warnings": []}
    recommendations = _db()["fleet_planning_recommendations"]
    cursor = recommendations.find({"zone_id": {"$in": zones}}).sort("forecast_date", 1).limit(25)
    rows = await cursor.to_list(length=25)
    warnings = [
        f"{row['demand_level']} demand expected in {row['zone_id']}"
        for row in rows
        if row.get("demand_level") in ["high", "very_high"]
    ]
    return {"zones": zones, "recommendations": serialize_mongo_list(rows), "warnings": warnings}


async def _get_maintenance_context(vehicle_id: str | None) -> dict[str, Any]:
    if not vehicle_id:
        return {"vehicle_id": None, "warnings": []}
    vehicle = await get_vehicle_by_id(vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vehicle does not exist")
    warnings = []
    if vehicle.get("health_status") == "critical":
        warnings.append("Selected vehicle has critical maintenance risk")
    elif vehicle.get("health_status") == "warning":
        warnings.append("Selected vehicle has warning maintenance status")
    return {"vehicle_id": vehicle_id, "health_status": vehicle.get("health_status"), "warnings": warnings}


def _segment_input(origin: dict[str, Any], destination: dict[str, Any], priority: str | None = None) -> dict[str, Any]:
    return {
        "pickup_latitude": origin["latitude"],
        "pickup_longitude": origin["longitude"],
        "drop_latitude": destination["latitude"],
        "drop_longitude": destination["longitude"],
        "priority": priority or destination.get("priority"),
        "weather": "Cloudy",
        "traffic": "Medium",
        "vehicle_type": "electric_van",
        "area": "urban",
        "category": "parcel",
    }


def build_ml_cost_matrix(points: list[dict[str, Any]], use_ml_cost: bool) -> tuple[list[list[int]], list[list[dict[str, Any]]], bool]:
    matrix: list[list[int]] = []
    predictions: list[list[dict[str, Any]]] = []
    used_ml = True
    for origin_index, origin in enumerate(points):
        row: list[int] = []
        prediction_row: list[dict[str, Any]] = []
        for destination_index, destination in enumerate(points):
            if origin_index == destination_index:
                row.append(0)
                prediction_row.append(
                    {
                        "distance_km": 0,
                        "predicted_eta_minutes": 0,
                        "delay_probability": 0,
                        "delay_prediction": 0,
                        "delay_risk_level": "low",
                        "route_cost_score": 0,
                    }
                )
                continue
            prediction, segment_used_ml = calculate_segment_cost(_segment_input(origin, destination), use_ml_cost=use_ml_cost)
            used_ml = used_ml and segment_used_ml
            row.append(max(int(round(prediction["route_cost_score"] * 100)), 1))
            prediction_row.append(prediction)
        matrix.append(row)
        predictions.append(prediction_row)
    return matrix, predictions, used_ml


def _nearest_neighbor_route(cost_matrix: list[list[int]]) -> list[int]:
    unvisited = set(range(1, len(cost_matrix)))
    route = [0]
    current = 0
    while unvisited:
        next_node = min(unvisited, key=lambda node: cost_matrix[current][node])
        route.append(next_node)
        unvisited.remove(next_node)
        current = next_node
    route.append(0)
    return route


def solve_single_vehicle_route(cost_matrix: list[list[int]]) -> list[int]:
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        return _nearest_neighbor_route(cost_matrix)

    manager = pywrapcp.RoutingIndexManager(len(cost_matrix), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return cost_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    solution = routing.SolveWithParameters(search_parameters)
    if solution is None:
        return _nearest_neighbor_route(cost_matrix)

    order = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        order.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    order.append(manager.IndexToNode(index))
    return order


async def _create_route_alert_once(title: str, message: str, severity: str, route_id: str | None = None, vehicle_id: str | None = None) -> None:
    query = {"alert_type": "route", "status": "active", "title": title}
    if await _db()[ALERT_COLLECTION].count_documents(query) > 0:
        return
    await create_alert(
        {
            "alert_type": "route",
            "severity": severity,
            "title": title,
            "message": message,
            "linked_vehicle_id": vehicle_id,
            "created_by_system": True,
        }
    )


async def save_route_plan(
    optimized_result: dict[str, Any],
    request_data: dict[str, Any],
    current_user: dict[str, Any],
) -> dict[str, Any]:
    vehicle_id = validate_object_id(request_data["vehicle_id"]) if request_data.get("vehicle_id") else None
    driver_id = validate_object_id(request_data["driver_id"]) if request_data.get("driver_id") else None
    created_by = validate_object_id(current_user["id"]) if current_user.get("id") else None
    document = build_route_plan_document(
        {
            **request_data,
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "delivery_order_ids": optimized_result["delivery_order_object_ids"],
            "optimized_stop_order": optimized_result["optimized_stop_order"],
            "total_predicted_eta_minutes": optimized_result["total_predicted_eta_minutes"],
            "total_route_cost_score": optimized_result["total_route_cost_score"],
            "average_delay_probability": optimized_result["average_delay_probability"],
            "optimization_method": optimized_result["optimization_method"],
            "demand_context": optimized_result.get("demand_context"),
            "maintenance_context": optimized_result.get("maintenance_context"),
            "created_by": created_by,
        }
    )
    result = await get_route_plan_collection().insert_one(document)
    route_id = result.inserted_id
    segment_documents = []
    for segment in optimized_result["segments"]:
        segment_documents.append(build_route_segment_document({**segment, "route_plan_id": route_id}))
    if segment_documents:
        await get_route_segment_collection().insert_many(segment_documents)
    return safe_route_document(await get_route_plan_collection().find_one({"_id": route_id}))


async def optimize_route(request_data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    points, order_ids = await build_points_from_orders_or_stops(request_data)
    demand_context = await _get_demand_context(points) if request_data.get("include_demand_context", True) else None
    maintenance_context = (
        await _get_maintenance_context(request_data.get("vehicle_id"))
        if request_data.get("include_maintenance_context", True)
        else None
    )
    cost_matrix, prediction_matrix, used_ml = build_ml_cost_matrix(points, request_data.get("use_ml_cost", True))
    route_order = solve_single_vehicle_route(cost_matrix)

    segments: list[dict[str, Any]] = []
    total_eta = 0.0
    total_cost = 0.0
    delay_values: list[float] = []
    for index in range(len(route_order) - 1):
        from_index = route_order[index]
        to_index = route_order[index + 1]
        prediction = prediction_matrix[from_index][to_index]
        total_eta += prediction["predicted_eta_minutes"]
        total_cost += prediction["route_cost_score"]
        delay_values.append(prediction["delay_probability"])
        segments.append(
            {
                "from_stop_index": from_index,
                "to_stop_index": to_index,
                "from_latitude": points[from_index]["latitude"],
                "from_longitude": points[from_index]["longitude"],
                "to_latitude": points[to_index]["latitude"],
                "to_longitude": points[to_index]["longitude"],
                **prediction,
            }
        )

    average_delay = round(sum(delay_values) / len(delay_values), 4) if delay_values else 0
    warnings = []
    if average_delay >= 0.70:
        warnings.append("High delay risk detected for optimized route")
    if demand_context:
        warnings.extend(demand_context.get("warnings", []))
    if maintenance_context:
        warnings.extend(maintenance_context.get("warnings", []))

    optimization_method = "ML-assisted OR-Tools single vehicle" if used_ml else "Distance-based OR-Tools single vehicle"
    result = {
        "route_id": None,
        "optimized_stop_order": format_optimized_stop_order(points, route_order),
        "total_predicted_eta_minutes": round(total_eta, 2),
        "total_route_cost_score": round(total_cost, 2),
        "average_delay_probability": average_delay,
        "optimization_method": optimization_method,
        "segments": segments,
        "warnings": warnings,
        "demand_context": demand_context,
        "maintenance_context": maintenance_context,
        "delivery_order_object_ids": order_ids,
        "used_ml_cost": used_ml,
    }
    if request_data.get("save_route", True):
        route_plan = await save_route_plan(result, request_data, current_user)
        result["route_id"] = route_plan["id"]
        result["route_code"] = route_plan["route_code"]
        if average_delay >= 0.70:
            await _create_route_alert_once(
                f"High delay risk detected for optimized route {route_plan['route_code']}",
                f"Average delay probability is {average_delay}. Review dispatch timing before release.",
                "high",
                route_id=route_plan["id"],
            )
        if maintenance_context and maintenance_context.get("health_status") == "critical":
            await _create_route_alert_once(
                f"Critical vehicle risk warning for route {route_plan['route_code']}",
                "Selected vehicle has critical maintenance risk.",
                "critical",
                route_id=route_plan["id"],
                vehicle_id=request_data.get("vehicle_id"),
            )
        if demand_context and demand_context.get("warnings"):
            await _create_route_alert_once(
                f"High demand route zone detected for {route_plan['route_code']}",
                "One or more stops are in high or very-high demand zones; additional capacity may be required.",
                "high",
                route_id=route_plan["id"],
            )
    return result


async def get_route_plan(route_id: str) -> dict[str, Any] | None:
    try:
        object_id = validate_object_id(route_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid route ID") from exc
    route = safe_route_document(await get_route_plan_collection().find_one({"_id": object_id}))
    if route:
        cursor = get_route_segment_collection().find({"route_plan_id": object_id}).sort("from_stop_index", 1)
        route["segments"] = serialize_mongo_list(await cursor.to_list(length=200))
    return route


async def list_route_plans(
    status_filter: str | None = None,
    vehicle_id: str | None = None,
    driver_id: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    query: dict[str, Any] = {}
    if status_filter:
        query["status"] = status_filter
    if vehicle_id:
        query["vehicle_id"] = validate_object_id(vehicle_id)
    if driver_id:
        query["driver_id"] = validate_object_id(driver_id)
    collection = get_route_plan_collection()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("created_at", -1).skip(calculate_skip(page, limit)).limit(limit)
    return build_pagination_response(serialize_mongo_list(await cursor.to_list(length=limit)), total, page, limit)


async def dispatch_route(route_id: str, dispatch_data: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        object_id = validate_object_id(route_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid route ID") from exc
    route = await get_route_plan_collection().find_one({"_id": object_id})
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    update: dict[str, Any] = {"status": "dispatched", "dispatched_at": utc_now(), "updated_at": utc_now()}
    if dispatch_data.get("vehicle_id"):
        update["vehicle_id"] = validate_object_id(dispatch_data["vehicle_id"])
    if dispatch_data.get("driver_id"):
        update["driver_id"] = validate_object_id(dispatch_data["driver_id"])
    await get_route_plan_collection().update_one({"_id": object_id}, {"$set": update})

    for order_id in route.get("delivery_order_ids", []):
        vehicle_value = update.get("vehicle_id") or route.get("vehicle_id")
        driver_value = update.get("driver_id") or route.get("driver_id")
        await update_delivery_order(
            str(order_id),
            {
                "delivery_status": "in_route",
                "assigned_vehicle_id": str(vehicle_value) if vehicle_value else None,
                "assigned_driver_id": str(driver_value) if driver_value else None,
            },
        )
    return await get_route_plan(route_id)


async def cancel_route(route_id: str, current_user: dict[str, Any]) -> dict[str, Any]:
    try:
        object_id = validate_object_id(route_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid route ID") from exc
    result = await get_route_plan_collection().update_one(
        {"_id": object_id},
        {"$set": {"status": "cancelled", "updated_at": utc_now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    return await get_route_plan(route_id)


async def get_route_dashboard_summary() -> dict[str, Any]:
    db = _db()
    route_collection = db[ROUTE_PLAN_COLLECTION]
    delivery_collection = db[DELIVERY_COLLECTION]
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [{"$group": {"_id": None, "average_delay": {"$avg": "$average_delay_probability"}}}]
    aggregate = await route_collection.aggregate(pipeline).to_list(length=1)
    stats = aggregate[0] if aggregate else {}
    today_eta_pipeline = [
        {"$match": {"created_at": {"$gte": today_start}}},
        {"$group": {"_id": None, "eta": {"$sum": "$total_predicted_eta_minutes"}}},
    ]
    eta_aggregate = await route_collection.aggregate(today_eta_pipeline).to_list(length=1)
    eta_stats = eta_aggregate[0] if eta_aggregate else {}
    return {
        "total_route_plans": await route_collection.count_documents({}),
        "optimized_routes_count": await route_collection.count_documents({"status": "optimized"}),
        "dispatched_routes_count": await route_collection.count_documents({"status": "dispatched"}),
        "active_routes_count": await route_collection.count_documents({"status": {"$in": ["dispatched", "in_progress"]}}),
        "average_route_delay_probability": round(float(stats.get("average_delay") or 0), 4),
        "total_predicted_eta_today": round(float(eta_stats.get("eta") or 0), 2),
        "pending_deliveries": await delivery_collection.count_documents({"delivery_status": "pending"}),
        "delivered_orders_today": await delivery_collection.count_documents(
            {"delivery_status": "delivered", "updated_at": {"$gte": today_start}}
        ),
    }
