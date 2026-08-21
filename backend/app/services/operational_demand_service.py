from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.delivery_model import DELIVERY_COLLECTION
from app.models.demand_model import DEMAND_FORECAST_COLLECTION, OPERATIONAL_DEMAND_DAILY_COLLECTION
from app.models.user_model import utc_now
from app.utils.demand_utils import estimate_required_vehicles, normalize_demand_level, safe_float
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


def calibration_values(actual_total: float, raw_total: float, history_days: int) -> tuple[str, float | None]:
    if history_days < 30 or raw_total <= 0:
        return "insufficient_history", None
    return "active", round(min(2.0, max(0.5, actual_total / raw_total)), 4)


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


async def forecast_vs_actual(zone_id: str | None = None, start_date: date | None = None, end_date: date | None = None) -> dict[str, Any]:
    actual_rows = await list_actuals(zone_id, start_date, end_date)
    actual_by_key = {
        (row["operational_zone_id"], datetime.fromisoformat(str(row["demand_date"]).replace("Z", "+00:00")).date()): row
        for row in actual_rows
    }
    forecast_query: dict[str, Any] = {}
    if zone_id:
        forecast_query["zone_id"] = source_zone_id(zone_id)
    forecast_rows = await _db()[DEMAND_FORECAST_COLLECTION].find(forecast_query).sort("forecast_date", 1).limit(5000).to_list(5000)
    forecast_by_key: dict[tuple[str, date], dict[str, Any]] = {}
    for row in forecast_rows:
        enriched = enrich_zone_record(row)
        forecast_by_key[(enriched["operational_zone_id"], row["forecast_date"].date())] = row

    calibration_by_zone: dict[str, tuple[str, float | None, int]] = {}
    yesterday = datetime.now(COLOMBO_TZ).date() - timedelta(days=1)
    for option in operational_zone_options():
        operational = str(option["operational_zone_id"])
        observed_dates = sorted(key[1] for key in actual_by_key if key[0] == operational and key[1] <= yesterday)
        history_days = 0
        actual_total = 0.0
        raw_total = 0.0
        if observed_dates:
            window_end = observed_dates[-1]
            window_start = window_end - timedelta(days=29)
            window_dates = [window_start + timedelta(days=index) for index in range(30)]
            if observed_dates[0] <= window_start and all((operational, value) in forecast_by_key for value in window_dates):
                history_days = 30
                actual_total = sum(safe_float(actual_by_key.get((operational, value), {}).get("total_orders")) for value in window_dates)
                raw_total = sum(safe_float(forecast_by_key[(operational, value)].get("predicted_demand")) for value in window_dates)
        status_value, factor = calibration_values(actual_total, raw_total, history_days)
        calibration_by_zone[operational] = (status_value, factor, history_days)

    items = []
    for raw in forecast_rows:
        enriched = enrich_zone_record(raw)
        operational = enriched["operational_zone_id"]
        value_date = raw["forecast_date"].date()
        if start_date and value_date < start_date:
            continue
        if end_date and value_date > end_date:
            continue
        status_value, factor, history_days = calibration_by_zone[operational]
        raw_forecast = safe_float(raw.get("predicted_demand"))
        final = raw_forecast if factor is None else raw_forecast * factor
        actual = actual_by_key.get((operational, value_date))
        items.append({
            "date": raw["forecast_date"],
            "operational_zone_id": operational,
            "zone_display_name": enriched["zone_display_name"],
            "raw_mapped_forecast": round(raw_forecast, 2),
            "local_actual_demand": actual.get("total_orders") if actual else None,
            "calibration_status": status_value,
            "calibration_factor": factor,
            "calibrated_forecast": round(final, 2) if factor is not None else None,
            "final_predicted_demand": round(final, 2),
            "history_days": history_days,
            "demand_level": normalize_demand_level(final),
            "estimated_required_vehicles": estimate_required_vehicles(final),
            "data_context": DATA_CONTEXT,
        })
    return {"items": items, "total": len(items), "data_context": DATA_CONTEXT}


def operational_zones() -> list[dict[str, Any]]:
    return operational_zone_options()
