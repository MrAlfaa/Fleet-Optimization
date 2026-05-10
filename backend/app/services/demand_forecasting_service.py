from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any

import pandas as pd
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.demand_model import (
    DEMAND_FORECAST_COLLECTION,
    DEMAND_MODEL_RUN_COLLECTION,
    DEMAND_ZONE_COLLECTION,
    FLEET_RECOMMENDATION_COLLECTION,
    build_demand_forecast_document,
    build_demand_model_run_document,
    build_demand_zone_document,
    build_fleet_recommendation_document,
    safe_demand_document,
)
from app.models.user_model import utc_now
from app.services.alert_service import create_alert
from app.services.demand_artifact_loader_service import (
    DEMAND_ARTIFACT_DIR,
    DemandArtifactUnavailableError,
    get_demand_artifact_status,
    load_demand_metrics,
    load_demand_model_bundle,
    load_fleet_planning_recommendations_csv,
    load_future_forecast_csv,
    load_zone_adjacency_graph,
    load_zone_metadata_csv,
)
from app.utils.demand_utils import (
    estimate_required_vehicles,
    normalize_demand_level,
    parse_forecast_date,
    recommended_action_from_demand_level,
    safe_float,
    standardize_forecast_record,
    standardize_planning_record,
    zone_display_fields,
)
from app.utils.object_id import serialize_mongo_list, validate_object_id
from app.utils.pagination import build_pagination_response, calculate_skip, normalize_pagination


DEMAND_ALLOWED_ROLES = ["admin", "fleet_manager", "route_planner"]


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not configured or connected")
    return db


def _object_id(value: str | None) -> ObjectId | None:
    if not value:
        return None
    try:
        return validate_object_id(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID") from exc


def _date_range_filter(start_date: str | None, end_date: str | None) -> dict[str, Any]:
    date_filter: dict[str, Any] = {}
    try:
        if start_date:
            date_filter["$gte"] = parse_forecast_date(start_date)
        if end_date:
            date_filter["$lte"] = parse_forecast_date(end_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return date_filter


async def get_model_status(load_model: bool = True) -> dict[str, Any]:
    return get_demand_artifact_status(load_model=load_model)


async def get_model_metrics() -> dict[str, Any]:
    return load_demand_metrics()


async def _upsert_zone(row: dict[str, Any]) -> None:
    zone_id = str(row["zone_id"])
    display = zone_display_fields(zone_id)
    zone_doc = build_demand_zone_document(
        {
            "zone_id": zone_id,
            "zone_name": display["zone_name"],
            "city": display["city"],
            "state": display["state"],
            "zone_lat": safe_float(row.get("zone_lat")) if "zone_lat" in row else None,
            "zone_lng": safe_float(row.get("zone_lng")) if "zone_lng" in row else None,
            "customer_count": int(safe_float(row.get("customer_count"), default=0)) if "customer_count" in row else None,
            "is_active": True,
        }
    )
    await _db()[DEMAND_ZONE_COLLECTION].update_one(
        {"zone_id": zone_id},
        {"$set": {k: v for k, v in zone_doc.items() if k != "created_at"}, "$setOnInsert": {"created_at": zone_doc["created_at"]}},
        upsert=True,
    )


async def _upsert_forecast(record: dict[str, Any], model_run_id: ObjectId | None = None) -> None:
    doc_data = {**record, "model_run_id": model_run_id}
    document = build_demand_forecast_document(doc_data)
    await _db()[DEMAND_FORECAST_COLLECTION].update_one(
        {
            "zone_id": document["zone_id"],
            "forecast_date": document["forecast_date"],
            "model_type": document["model_type"],
        },
        {"$set": document},
        upsert=True,
    )


async def _upsert_recommendation(record: dict[str, Any]) -> None:
    document = build_fleet_recommendation_document(record)
    await _db()[FLEET_RECOMMENDATION_COLLECTION].update_one(
        {"zone_id": document["zone_id"], "forecast_date": document["forecast_date"]},
        {"$set": document},
        upsert=True,
    )


async def _create_model_run(
    run_type: str,
    records_generated: int,
    zones_count: int,
    forecast_dates: list[datetime],
    current_user: dict[str, Any] | None,
    status_value: str = "completed",
) -> ObjectId:
    user_id = _object_id(current_user.get("id")) if current_user else None
    document = build_demand_model_run_document(
        {
            "run_type": run_type,
            "model_name": "Graph-Enhanced Prophet",
            "artifact_source": str(DEMAND_ARTIFACT_DIR),
            "metrics_snapshot": load_demand_metrics(),
            "forecast_start_date": min(forecast_dates) if forecast_dates else None,
            "forecast_end_date": max(forecast_dates) if forecast_dates else None,
            "zones_count": zones_count,
            "records_generated": records_generated,
            "status": status_value,
            "created_by": user_id,
        }
    )
    result = await _db()[DEMAND_MODEL_RUN_COLLECTION].insert_one(document)
    return result.inserted_id


async def _create_demand_alert_if_needed(record: dict[str, Any]) -> bool:
    level = record["demand_level"]
    if level not in {"high", "very_high"}:
        return False

    severity = "critical" if level == "very_high" else "high"
    date_label = record["forecast_date"].date().isoformat()
    title = f"{level.replace('_', ' ').title()} demand expected in {record['zone_id']} on {date_label}"
    existing = await _db()[ALERT_COLLECTION].find_one({"alert_type": "demand", "title": title, "status": "active"})
    if existing:
        return False

    await create_alert(
        {
            "alert_type": "demand",
            "severity": severity,
            "title": title,
            "message": (
                f"{level.replace('_', ' ').title()} parcel demand forecasted for {record['zone_id']} "
                f"on {date_label}. Predicted demand: {record['predicted_demand']:.2f}. "
                f"{record['recommended_action']}"
            ),
            "created_by_system": True,
        }
    )
    return True


async def import_artifact_forecasts_to_database(current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    status_data = get_demand_artifact_status(load_model=False)
    if status_data["missing_files"]:
        raise DemandArtifactUnavailableError(
            "Demand forecasting artifact is unavailable",
            {"missing_files": status_data["missing_files"], "artifact_path": status_data["artifact_path"]},
        )

    zones_df = load_zone_metadata_csv()
    forecast_df = load_future_forecast_csv()
    planning_df = load_fleet_planning_recommendations_csv()

    for row in zones_df.to_dict(orient="records"):
        await _upsert_zone(row)

    forecast_records = [standardize_forecast_record(row, horizon_days=30) for row in forecast_df.to_dict(orient="records")]
    planning_records = [standardize_planning_record(row) for row in planning_df.to_dict(orient="records")]
    forecast_dates = [record["forecast_date"] for record in forecast_records]
    model_run_id = await _create_model_run(
        "artifact_import",
        records_generated=len(forecast_records),
        zones_count=len(zones_df),
        forecast_dates=forecast_dates,
        current_user=current_user,
    )

    for record in forecast_records:
        await _upsert_forecast(record, model_run_id=model_run_id)

    alerts_created = 0
    for record in planning_records:
        await _upsert_recommendation(record)
        if await _create_demand_alert_if_needed(record):
            alerts_created += 1

    return {
        "zones_imported": len(zones_df),
        "forecast_records": len(forecast_records),
        "planning_records": len(planning_records),
        "alerts_created": alerts_created,
        "model_run_id": str(model_run_id),
    }


async def list_zones(search: str | None = None, page: int = 1, limit: int = 20) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    query: dict[str, Any] = {}
    if search:
        query["$or"] = [
            {"zone_id": {"$regex": search, "$options": "i"}},
            {"zone_name": {"$regex": search, "$options": "i"}},
            {"city": {"$regex": search, "$options": "i"}},
            {"state": {"$regex": search, "$options": "i"}},
        ]
    collection = _db()[DEMAND_ZONE_COLLECTION]
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("zone_id", 1).skip(calculate_skip(page, limit)).limit(limit)
    return build_pagination_response(serialize_mongo_list(await cursor.to_list(length=limit)), total, page, limit)


async def list_forecasts(
    zone_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    demand_level: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    query: dict[str, Any] = {}
    if zone_id:
        query["zone_id"] = zone_id
    date_filter = _date_range_filter(start_date, end_date)
    if date_filter:
        query["forecast_date"] = date_filter
    if demand_level:
        if demand_level not in {"low", "medium", "high", "very_high"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid demand level")
        thresholds = {
            "low": {"$lt": 25},
            "medium": {"$gte": 25, "$lt": 50},
            "high": {"$gte": 50, "$lt": 80},
            "very_high": {"$gte": 80},
        }
        query["predicted_demand"] = thresholds[demand_level]

    collection = _db()[DEMAND_FORECAST_COLLECTION]
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("forecast_date", 1).skip(calculate_skip(page, limit)).limit(limit)
    return build_pagination_response(serialize_mongo_list(await cursor.to_list(length=limit)), total, page, limit)


async def get_zone_forecast(zone_id: str, days: int = 30) -> dict[str, Any]:
    days = min(max(days, 1), 365)
    cursor = _db()[DEMAND_FORECAST_COLLECTION].find({"zone_id": zone_id}).sort("forecast_date", 1).limit(days)
    items = serialize_mongo_list(await cursor.to_list(length=days))
    return {"zone_id": zone_id, "days": days, "items": items}


async def get_fleet_planning_recommendations(
    zone_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    demand_level: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    query: dict[str, Any] = {}
    if zone_id:
        query["zone_id"] = zone_id
    date_filter = _date_range_filter(start_date, end_date)
    if date_filter:
        query["forecast_date"] = date_filter
    if demand_level:
        if demand_level not in {"low", "medium", "high", "very_high"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid demand level")
        query["demand_level"] = demand_level

    collection = _db()[FLEET_RECOMMENDATION_COLLECTION]
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("forecast_date", 1).skip(calculate_skip(page, limit)).limit(limit)
    return build_pagination_response(serialize_mongo_list(await cursor.to_list(length=limit)), total, page, limit)


def _apply_graph_enhancement_to_forecast(baseline_df: pd.DataFrame, adjacency: dict[str, Any], alpha: float = 0.25) -> pd.DataFrame:
    enhanced_rows: list[dict[str, Any]] = []
    lookup = baseline_df.set_index(["zone_id", "ds"])["yhat"].to_dict()

    for _, row in baseline_df.iterrows():
        zone = row["zone_id"]
        forecast_date = row["ds"]
        base_yhat = safe_float(row["yhat"])
        neighbors = adjacency.get(zone, [])
        weighted = 0.0
        total_weight = 0.0
        for neighbor in neighbors:
            neighbor_zone = neighbor.get("neighbor")
            weight = safe_float(neighbor.get("weight"))
            neighbor_forecast = lookup.get((neighbor_zone, forecast_date))
            if neighbor_forecast is not None:
                weighted += weight * safe_float(neighbor_forecast)
                total_weight += weight
        graph_yhat = base_yhat if total_weight <= 0 else ((1 - alpha) * base_yhat) + (alpha * (weighted / total_weight))
        graph_yhat = max(0, graph_yhat)
        enhanced_rows.append(
            {
                "zone_id": zone,
                "ds": forecast_date,
                "baseline_prophet_forecast": round(base_yhat, 2),
                "baseline_yhat": round(base_yhat, 2),
                "final_graph_enhanced_forecast": round(graph_yhat, 2),
                "predicted_demand": round(graph_yhat, 2),
            }
        )
    return pd.DataFrame(enhanced_rows)


def _forecast_from_model_bundle(days: int) -> pd.DataFrame:
    bundle = load_demand_model_bundle()
    models = bundle.get("final_prophet_models") or {}
    adjacency = bundle.get("adjacency") or {}
    configuration = bundle.get("configuration") or {}
    alpha = safe_float(configuration.get("alpha_spatial_influence"), default=0.25)
    if not models:
        raise DemandArtifactUnavailableError("Demand forecasting model bundle has no Prophet models", {"artifact_path": str(DEMAND_ARTIFACT_DIR)})

    baseline_rows: list[pd.DataFrame] = []
    for zone, model in models.items():
        future = model.make_future_dataframe(periods=days, freq="D")
        forecast = model.predict(future)
        max_history_date = forecast["ds"].max() - pd.Timedelta(days=days)
        future_forecast = forecast[forecast["ds"] > max_history_date].copy()
        future_forecast["zone_id"] = zone
        future_forecast["yhat"] = future_forecast["yhat"].clip(lower=0)
        baseline_rows.append(future_forecast[["zone_id", "ds", "yhat"]])

    return _apply_graph_enhancement_to_forecast(pd.concat(baseline_rows, ignore_index=True), adjacency, alpha=alpha)


async def refresh_forecast_from_model(days: int = 30, save_to_database: bool = True, source: str = "artifact", current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    days = min(max(days, 1), 365)
    fallback_used = False
    fallback_reason = None
    if source == "model":
        try:
            forecast_df = _forecast_from_model_bundle(days)
        except Exception as exc:
            fallback_used = True
            fallback_reason = str(exc)
            forecast_df = load_future_forecast_csv().head(days * 10)
    else:
        forecast_df = load_future_forecast_csv().head(days * 10)

    forecast_records = [standardize_forecast_record(row, horizon_days=days) for row in forecast_df.to_dict(orient="records")]
    planning_records = [
        {
            "zone_id": record["zone_id"],
            "forecast_date": record["forecast_date"],
            "predicted_demand": record["predicted_demand"],
            "demand_level": normalize_demand_level(record["predicted_demand"]),
            "estimated_required_vehicles": estimate_required_vehicles(record["predicted_demand"]),
            "recommended_action": recommended_action_from_demand_level(normalize_demand_level(record["predicted_demand"])),
        }
        for record in forecast_records
    ]

    model_run_id = None
    alerts_created = 0
    if save_to_database:
        model_run_id = await _create_model_run(
            "model_forecast" if source == "model" and not fallback_used else "manual_refresh",
            records_generated=len(forecast_records),
            zones_count=len({record["zone_id"] for record in forecast_records}),
            forecast_dates=[record["forecast_date"] for record in forecast_records],
            current_user=current_user,
            status_value="partial" if fallback_used else "completed",
        )
        for record in forecast_records:
            await _upsert_forecast(record, model_run_id=model_run_id)
        for record in planning_records:
            await _upsert_recommendation(record)
            if await _create_demand_alert_if_needed(record):
                alerts_created += 1

    return {
        "source_requested": source,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "forecast_records": len(forecast_records),
        "planning_records": len(planning_records),
        "alerts_created": alerts_created,
        "model_run_id": str(model_run_id) if model_run_id else None,
        "items": forecast_records[:50],
    }


async def get_demand_dashboard_summary() -> dict[str, Any]:
    db = _db()
    forecast_collection = db[DEMAND_FORECAST_COLLECTION]
    recommendation_collection = db[FLEET_RECOMMENDATION_COLLECTION]
    first_forecast = await forecast_collection.find_one({}, sort=[("forecast_date", 1)])
    latest = await forecast_collection.find_one({}, sort=[("forecast_date", -1)])
    if first_forecast:
        window_start = first_forecast["forecast_date"]
        window_end = window_start + timedelta(days=7)
        next_7_query = {"forecast_date": {"$gte": window_start, "$lt": window_end}}
    else:
        next_7_query = {"forecast_date": {"$exists": False}}

    high_zones = await recommendation_collection.distinct("zone_id", {"demand_level": "high"})
    very_high_zones = await recommendation_collection.distinct("zone_id", {"demand_level": "very_high"})
    demand_sum = await forecast_collection.aggregate(
        [{"$match": next_7_query}, {"$group": {"_id": None, "total": {"$sum": "$predicted_demand"}}}]
    ).to_list(length=1)
    vehicles_sum = await recommendation_collection.aggregate(
        [{"$match": next_7_query}, {"$group": {"_id": None, "total": {"$sum": "$estimated_required_vehicles"}}}]
    ).to_list(length=1)
    top_zones = await forecast_collection.aggregate(
        [
            {"$match": next_7_query},
            {"$group": {"_id": "$zone_id", "predicted_demand": {"$sum": "$predicted_demand"}}},
            {"$sort": {"predicted_demand": -1}},
            {"$limit": 5},
        ]
    ).to_list(length=5)
    return {
        "total_zones": await db[DEMAND_ZONE_COLLECTION].count_documents({"is_active": True}),
        "forecast_records": await forecast_collection.count_documents({}),
        "high_demand_zones": len(high_zones),
        "very_high_demand_zones": len(very_high_zones),
        "total_predicted_demand_next_7_days": demand_sum[0]["total"] if demand_sum else 0,
        "total_required_vehicles_next_7_days": vehicles_sum[0]["total"] if vehicles_sum else 0,
        "top_demand_zones": [{"zone_id": row["_id"], "predicted_demand": row["predicted_demand"]} for row in top_zones],
        "latest_forecast_date": latest["forecast_date"].isoformat() if latest else None,
    }


async def get_latest_forecast_summary() -> dict[str, Any]:
    return await get_demand_dashboard_summary()


async def get_zone_adjacency_graph() -> dict[str, Any]:
    return load_zone_adjacency_graph()


async def export_forecasts_as_csv() -> str:
    cursor = _db()[DEMAND_FORECAST_COLLECTION].find({}).sort([("zone_id", 1), ("forecast_date", 1)])
    rows = serialize_mongo_list(await cursor.to_list(length=10000))
    output = StringIO()
    if not rows:
        pd.DataFrame(columns=["zone_id", "forecast_date", "predicted_demand", "model_type"]).to_csv(output, index=False)
    else:
        pd.DataFrame(rows).to_csv(output, index=False)
    return output.getvalue()
