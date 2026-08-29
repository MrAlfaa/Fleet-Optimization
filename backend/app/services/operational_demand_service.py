from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.delivery_model import DELIVERY_COLLECTION
from app.models.demand_model import (
    DEMAND_ACTIVE_RUN_COLLECTION,
    DEMAND_ACTIVE_RUN_POINTER_ID,
    DEMAND_FORECAST_COLLECTION,
    OPERATIONAL_DEMAND_DAILY_COLLECTION,
)
from app.models.user_model import utc_now
from app.utils.demand_utils import (
    estimate_required_vehicles,
    normalize_demand_level,
    recommended_action_from_demand_level,
    safe_float,
)
from app.utils.object_id import serialize_mongo_document
from app.utils.sri_lanka_zones import DATA_CONTEXT, enrich_zone_record, operational_zone_options, source_zone_id


COLOMBO_TZ = ZoneInfo("Asia/Colombo")
STATUS_FIELDS = {
    "pending": "pending_orders",
    "assigned": "assigned_orders",
    "in_route": "in_route_orders",
    "delivered": "delivered_orders",
    "failed": "failed_orders",
    "rescheduled": "rescheduled_orders",
    "cancelled": "cancelled_orders",
}


def _db():
    database = get_database()
    if database is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return database


def demand_day(value: datetime | None) -> date:
    moment = value or utc_now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=COLOMBO_TZ)
    return moment.astimezone(COLOMBO_TZ).date()


def day_bounds(value: date) -> tuple[datetime, datetime]:
    start = datetime.combine(value, time.min, tzinfo=COLOMBO_TZ)
    return start, start + timedelta(days=1)


async def recalculate_operational_demand_day(operational_zone_id: str, value: date) -> dict[str, Any]:
    start, end = day_bounds(value)
    orders = await _db()[DELIVERY_COLLECTION].find({
        "zone_id": operational_zone_id,
        "is_demo": {"$ne": True},
        "$or": [
            {"scheduled_date": {"$gte": start, "$lt": end}},
            {"scheduled_date": None, "created_at": {"$gte": start, "$lt": end}},
        ],
    }).to_list(length=10000)
    status_counts = {field: 0 for field in STATUS_FIELDS.values()}
    for order in orders:
        field = STATUS_FIELDS.get(str(order.get("delivery_status") or "pending"))
        if field:
            status_counts[field] += 1
    non_cancelled = [order for order in orders if order.get("delivery_status") != "cancelled"]
    now = utc_now()
    document = {
        "operational_zone_id": operational_zone_id,
        "source_zone_id": source_zone_id(operational_zone_id),
        "demand_date": start,
        "total_orders": len(non_cancelled),
        **status_counts,
        "total_parcel_weight": round(sum(safe_float(order.get("parcel_weight")) for order in non_cancelled), 2),
        "total_parcel_volume": round(sum(safe_float(order.get("parcel_volume")) for order in non_cancelled), 2),
        "source": "delivery_orders",
        "updated_at": now,
    }
    await _db()[OPERATIONAL_DEMAND_DAILY_COLLECTION].update_one(
        {"operational_zone_id": operational_zone_id, "demand_date": start},
        {"$set": document, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return document


async def recalculate_for_delivery(order: dict[str, Any] | None) -> None:
    if not order or order.get("is_demo") or not order.get("zone_id"):
        return
    await recalculate_operational_demand_day(str(order["zone_id"]), demand_day(order.get("scheduled_date")))


async def rebuild_operational_demand() -> dict[str, int]:
    keys: set[tuple[str, date]] = set()
    async for order in _db()[DELIVERY_COLLECTION].find(
        {"zone_id": {"$regex": "^LK_"}, "is_demo": {"$ne": True}},
        {"zone_id": 1, "scheduled_date": 1},
    ):
        keys.add((str(order["zone_id"]), demand_day(order.get("scheduled_date"))))
    for zone_id, value in sorted(keys):
        await recalculate_operational_demand_day(zone_id, value)
    return {"days_rebuilt": len(keys), "zones_count": len({key[0] for key in keys})}


async def list_actuals(zone_id: str | None = None, start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if zone_id:
        query["operational_zone_id"] = zone_id
    if start_date or end_date:
        bounds: dict[str, datetime] = {}
        if start_date:
            bounds["$gte"] = day_bounds(start_date)[0]
        if end_date:
            bounds["$lt"] = day_bounds(end_date)[1]
        query["demand_date"] = bounds
    rows = await _db()[OPERATIONAL_DEMAND_DAILY_COLLECTION].find(query).sort("demand_date", 1).limit(5000).to_list(5000)
    result = []
    for row in rows:
        safe = serialize_mongo_document(row) or {}
        result.append(enrich_zone_record({**safe, "zone_id": safe["operational_zone_id"]}))
    return result


def _comparison_item(forecast: dict[str, Any], actual_orders: int | None) -> dict[str, Any]:
    enriched = enrich_zone_record(forecast)
    predicted = round(safe_float(forecast.get("predicted_demand")), 2)
    variance = round(predicted - actual_orders, 2) if actual_orders is not None else None
    variance_percentage = (
        round((variance / actual_orders) * 100, 2)
        if variance is not None and actual_orders not in {None, 0}
        else None
    )
    level = normalize_demand_level(predicted)
    return {
        "date": forecast["forecast_date"],
        "operational_zone_id": enriched["operational_zone_id"],
        "zone_display_name": enriched["zone_display_name"],
        "predicted_demand": predicted,
        "final_predicted_demand": predicted,
        "local_actual_demand": actual_orders,
        "variance_orders": variance,
        "variance_percentage": variance_percentage,
        "baseline_forecast": (
            round(safe_float(forecast.get("baseline_prophet_forecast")), 2)
            if forecast.get("baseline_prophet_forecast") is not None
            else None
        ),
        "lower_bound": round(safe_float(forecast.get("lower_bound")), 2) if forecast.get("lower_bound") is not None else None,
        "upper_bound": round(safe_float(forecast.get("upper_bound")), 2) if forecast.get("upper_bound") is not None else None,
        "demand_level": level,
        "estimated_required_vehicles": estimate_required_vehicles(predicted),
        "recommended_action": recommended_action_from_demand_level(level),
        "model_version": forecast.get("model_version"),
        "generated_at": forecast.get("created_at"),
    }


async def forecast_vs_actual(
    zone_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    *,
    model_run_id: ObjectId | None = None,
    active_run_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actual_rows = await list_actuals(zone_id, start_date, end_date)
    actual_by_key = {
        (row["operational_zone_id"], datetime.fromisoformat(str(row["demand_date"]).replace("Z", "+00:00")).date()): row
        for row in actual_rows
    }
    active_run_id = model_run_id
    if active_run_id is None:
        pointer = await _db()[DEMAND_ACTIVE_RUN_COLLECTION].find_one({"_id": DEMAND_ACTIVE_RUN_POINTER_ID})
        active_run_id = pointer.get("model_run_id") if pointer else None
    if active_run_id is None:
        return {"items": [], "total": 0, "data_context": DATA_CONTEXT, "active_run": None}
    forecast_query: dict[str, Any] = {"model_run_id": active_run_id}
    if zone_id:
        forecast_query["zone_id"] = zone_id
    forecast_rows = await _db()[DEMAND_FORECAST_COLLECTION].find(forecast_query).sort("forecast_date", 1).limit(5000).to_list(5000)
    items = []
    for raw in forecast_rows:
        enriched = enrich_zone_record(raw)
        operational = enriched["operational_zone_id"]
        value_date = raw["forecast_date"].date()
        if start_date and value_date < start_date:
            continue
        if end_date and value_date > end_date:
            continue
        actual = actual_by_key.get((operational, value_date))
        items.append(_comparison_item(raw, actual.get("total_orders") if actual else None))
    if active_run_metadata is None:
        from app.services.demand_forecasting_service import _active_run_metadata

        active_run_metadata = await _active_run_metadata()
    return {
        "items": items,
        "total": len(items),
        "data_context": DATA_CONTEXT,
        "active_run": active_run_metadata,
    }


def operational_zones() -> list[dict[str, Any]]:
    return operational_zone_options()
