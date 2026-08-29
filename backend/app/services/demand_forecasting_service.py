from datetime import datetime, timedelta, timezone
from io import StringIO
import hashlib
import json
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo import UpdateOne
from pymongo.errors import DuplicateKeyError

from app.core.database import get_database
from app.models.alert_model import ALERT_COLLECTION
from app.models.demand_model import (
    DEMAND_ACTIVE_RUN_COLLECTION,
    DEMAND_ACTIVE_RUN_POINTER_ID,
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
    load_demand_artifacts,
    load_demand_metrics,
    load_future_forecast_csv,
    load_zone_adjacency_graph,
    load_zone_metadata_csv,
)
from app.services.demand_artifact_registry import MODEL_VERSION
from app.utils.demand_utils import (
    estimate_required_vehicles,
    normalize_demand_level,
    parse_forecast_date,
    recommended_action_from_demand_level,
    safe_float,
    standardize_forecast_record,
    zone_display_fields,
)
from app.utils.object_id import serialize_mongo_list, validate_object_id
from app.utils.pagination import build_pagination_response, calculate_skip, normalize_pagination
from app.utils.sri_lanka_zones import DATA_CONTEXT, enrich_zone_record, operational_zone_id, operational_zone_options


DEMAND_ALLOWED_ROLES = ["admin", "fleet_manager", "route_planner"]
APPROVED_REFRESH_HORIZONS = {7, 14, 30}
COLOMBO_TIMEZONE = ZoneInfo("Asia/Colombo")


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
    result = get_demand_artifact_status(load_model=load_model)
    active = await _active_run_metadata()
    return {
        **result,
        "active_run": active,
        "planning_window": active.get("planning_window") if active else None,
        "operational_state": "degraded" if result.get("degraded") else "ready",
    }


async def get_model_metrics() -> dict[str, Any]:
    return load_demand_metrics()


def _iso_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _planning_window_metadata(run: dict[str, Any]) -> dict[str, Any]:
    metrics = run.get("metrics_snapshot") or {}
    dataset_end = (metrics.get("dataset") or {}).get("end")
    return {
        "basis": "colombo_business_date",
        "dataset_end_date": str(dataset_end) if dataset_end else None,
        "forecast_start_date": _iso_datetime(run.get("forecast_start_date")),
        "forecast_end_date": _iso_datetime(run.get("forecast_end_date")),
        "horizon_days": int(run.get("horizon_days") or 0),
    }


def _run_metadata(run: dict[str, Any], *, include_status: bool = False) -> dict[str, Any]:
    safe = safe_demand_document(run) or {}
    metadata = {
        "model_run_id": safe.get("id"),
        "run_type": run.get("run_type"),
        "model_version": run.get("model_version") or run.get("model_name"),
        "horizon_days": int(run.get("horizon_days") or 0),
        "source_requested": run.get("source_requested"),
        "effective_source": run.get("effective_source") or run.get("source_requested"),
        "fallback_used": bool(run.get("fallback_used", False)),
        "request_fingerprint": run.get("request_fingerprint"),
        "forecast_start_date": _iso_datetime(run.get("forecast_start_date")),
        "forecast_end_date": _iso_datetime(run.get("forecast_end_date")),
        "zones_count": int(run.get("zones_count") or 0),
        "records_generated": int(run.get("records_generated") or 0),
        "generated_at": _iso_datetime(run.get("generated_at") or run.get("created_at")),
        "activated_at": _iso_datetime(run.get("activated_at")),
        "planning_window": _planning_window_metadata(run),
    }
    if include_status:
        metadata["status"] = run.get("status")
        metadata["failed_at"] = _iso_datetime(run.get("failed_at"))
    return metadata


async def _active_run_document() -> dict[str, Any] | None:
    pointer = await _db()[DEMAND_ACTIVE_RUN_COLLECTION].find_one({"_id": DEMAND_ACTIVE_RUN_POINTER_ID})
    if not pointer or not pointer.get("model_run_id"):
        return None
    return await _db()[DEMAND_MODEL_RUN_COLLECTION].find_one({"_id": pointer["model_run_id"], "status": "completed"})


async def _active_run_metadata() -> dict[str, Any] | None:
    run = await _active_run_document()
    return _run_metadata(run) if run else None


async def list_demand_runs(limit: int = 20) -> dict[str, Any]:
    current_dataset_end = (load_demand_metrics().get("dataset") or {}).get("end")
    query: dict[str, Any] = {
        "status": {"$in": ["completed", "failed"]},
        "model_version": MODEL_VERSION,
    }
    if current_dataset_end:
        # Preserve superseded runs in MongoDB for audit history, while keeping
        # the operational cycle list scoped to the currently approved dataset.
        query["metrics_snapshot.dataset.end"] = current_dataset_end
    cursor = (
        _db()[DEMAND_MODEL_RUN_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .limit(limit)
    )
    runs = await cursor.to_list(length=limit)
    return {"items": [_run_metadata(run, include_status=True) for run in runs], "limit": limit}


async def get_demand_run_forecasts(
    run_id: str,
    *,
    zone_id: str | None = None,
    page: int = 1,
    limit: int = 100,
) -> dict[str, Any]:
    try:
        run_oid = validate_object_id(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid demand forecast run ID") from exc

    current_dataset_end = (load_demand_metrics().get("dataset") or {}).get("end")
    run_query: dict[str, Any] = {
        "_id": run_oid,
        "status": "completed",
        "model_version": MODEL_VERSION,
    }
    if current_dataset_end:
        run_query["metrics_snapshot.dataset.end"] = current_dataset_end
    run = await _db()[DEMAND_MODEL_RUN_COLLECTION].find_one(run_query)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demand forecast run was not found")

    page, limit = normalize_pagination(page, min(limit, 500))
    forecast_query: dict[str, Any] = {"model_run_id": run_oid}
    if zone_id:
        forecast_query["zone_id"] = operational_zone_id(zone_id)
    collection = _db()[DEMAND_FORECAST_COLLECTION]
    total = await collection.count_documents(forecast_query)
    cursor = (
        collection.find(forecast_query)
        .sort([("forecast_date", 1), ("zone_id", 1)])
        .skip(calculate_skip(page, limit))
        .limit(limit)
    )
    items = [
        enrich_zone_record(_add_forecast_planning_fields(row))
        for row in serialize_mongo_list(await cursor.to_list(length=limit))
    ]
    return {
        **build_pagination_response(items, total, page, limit),
        "run": _run_metadata(run, include_status=True),
    }


def _request_fingerprint(model_version: str, source: str, horizon_days: int, forecast_start: datetime) -> str:
    payload = {
        "forecast_start": forecast_start.date().isoformat(),
        "horizon_days": int(horizon_days),
        "model_version": model_version,
        "source": source,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


async def _reusable_active_run(request_fingerprint: str, effective_source: str) -> dict[str, Any] | None:
    run = await _active_run_document()
    if (
        run
        and run.get("request_fingerprint") == request_fingerprint
        and (run.get("effective_source") or run.get("source_requested")) == effective_source
        and bool(run.get("fallback_used", False)) == (effective_source == "artifact_fallback")
    ):
        return run
    return None


async def get_active_run_id() -> ObjectId | None:
    pointer = await _db()[DEMAND_ACTIVE_RUN_COLLECTION].find_one({"_id": DEMAND_ACTIVE_RUN_POINTER_ID})
    return pointer.get("model_run_id") if pointer else None


def _validate_complete_run(
    forecasts: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    *,
    expected_zone_ids: set[str],
    expected_days: int,
    expected_start: datetime,
) -> dict[str, Any]:
    expected_start = expected_start if expected_start.tzinfo else expected_start.replace(tzinfo=timezone.utc)
    expected_dates = {expected_start.date() + timedelta(days=index) for index in range(expected_days)}

    def keys(rows: list[dict[str, Any]]) -> set[tuple[str, Any]]:
        return {(str(row["zone_id"]), parse_forecast_date(row["forecast_date"]).date()) for row in rows}

    expected_keys = {(zone, value) for zone in expected_zone_ids for value in expected_dates}
    forecast_keys = keys(forecasts)
    recommendation_keys = keys(recommendations)
    if forecast_keys != expected_keys or recommendation_keys != expected_keys:
        raise ValueError("Demand run is not complete for every operational zone and forecast date")
    if len(forecasts) != len(expected_keys) or len(recommendations) != len(expected_keys):
        raise ValueError("Demand run contains duplicate or incomplete operational records")
    return {
        "records": len(forecasts),
        "zones": len(expected_zone_ids),
        "days": expected_days,
        "forecast_start_date": expected_start,
        "forecast_end_date": expected_start + timedelta(days=expected_days - 1),
    }


async def _upsert_zone(row: dict[str, Any]) -> None:
    zone_id = str(row["zone_id"])
    display = zone_display_fields(zone_id)
    zone_doc = build_demand_zone_document(
        {
            "zone_id": zone_id,
            "zone_name": display["zone_name"],
            "city": display["city"],
            "state": display["state"],
            "zone_lat": safe_float(row.get("zone_lat", row.get("latitude"))) if "zone_lat" in row or "latitude" in row else None,
            "zone_lng": safe_float(row.get("zone_lng", row.get("longitude"))) if "zone_lng" in row or "longitude" in row else None,
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
    doc_data = {**record, "model_run_id": model_run_id, "model_version": MODEL_VERSION}
    document = build_demand_forecast_document(doc_data)
    await _db()[DEMAND_FORECAST_COLLECTION].update_one(
        {
            "model_run_id": model_run_id,
            "zone_id": document["zone_id"],
            "forecast_date": document["forecast_date"],
            "model_type": document["model_type"],
        },
        {"$set": document},
        upsert=True,
    )


async def _upsert_recommendation(record: dict[str, Any], model_run_id: ObjectId | None = None) -> None:
    document = build_fleet_recommendation_document({**record, "model_run_id": model_run_id, "model_version": MODEL_VERSION})
    await _db()[FLEET_RECOMMENDATION_COLLECTION].update_one(
        {"model_run_id": model_run_id, "zone_id": document["zone_id"], "forecast_date": document["forecast_date"]},
        {"$set": document},
        upsert=True,
    )


async def _persist_forecast_run(
    forecasts: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    model_run_id: ObjectId,
) -> None:
    forecast_operations = []
    for record in forecasts:
        document = build_demand_forecast_document({**record, "model_run_id": model_run_id, "model_version": MODEL_VERSION})
        forecast_operations.append(UpdateOne(
            {
                "model_run_id": model_run_id,
                "zone_id": document["zone_id"],
                "forecast_date": document["forecast_date"],
                "model_type": document["model_type"],
            },
            {"$set": document},
            upsert=True,
        ))

    recommendation_operations = []
    for record in recommendations:
        document = build_fleet_recommendation_document({**record, "model_run_id": model_run_id, "model_version": MODEL_VERSION})
        recommendation_operations.append(UpdateOne(
            {"model_run_id": model_run_id, "zone_id": document["zone_id"], "forecast_date": document["forecast_date"]},
            {"$set": document},
            upsert=True,
        ))

    if forecast_operations:
        await _db()[DEMAND_FORECAST_COLLECTION].bulk_write(forecast_operations, ordered=False)
    if recommendation_operations:
        await _db()[FLEET_RECOMMENDATION_COLLECTION].bulk_write(recommendation_operations, ordered=False)


async def _create_model_run(
    run_type: str,
    records_generated: int,
    zones_count: int,
    forecast_dates: list[datetime],
    current_user: dict[str, Any] | None,
    horizon_days: int,
    source_requested: str,
    effective_source: str,
    fallback_used: bool,
    request_fingerprint: str,
    status_value: str = "staging",
) -> ObjectId:
    user_id = _object_id(current_user.get("id")) if current_user else None
    document = build_demand_model_run_document(
        {
            "run_type": run_type,
            "model_name": MODEL_VERSION,
            "model_version": MODEL_VERSION,
            "artifact_source": str(DEMAND_ARTIFACT_DIR),
            "metrics_snapshot": load_demand_metrics(),
            "forecast_start_date": min(forecast_dates) if forecast_dates else None,
            "forecast_end_date": max(forecast_dates) if forecast_dates else None,
            "zones_count": zones_count,
            "records_generated": records_generated,
            "status": status_value,
            "horizon_days": horizon_days,
            "source_requested": source_requested,
            "effective_source": effective_source,
            "fallback_used": fallback_used,
            "request_fingerprint": request_fingerprint,
            "created_by": user_id,
        }
    )
    try:
        result = await _db()[DEMAND_MODEL_RUN_COLLECTION].insert_one(document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An identical demand forecast generation is already in progress",
        ) from exc
    return result.inserted_id


async def _activate_complete_run(model_run_id: ObjectId, validation: dict[str, Any]) -> None:
    db = _db()
    forecast_count = await db[DEMAND_FORECAST_COLLECTION].count_documents({"model_run_id": model_run_id})
    recommendation_count = await db[FLEET_RECOMMENDATION_COLLECTION].count_documents({"model_run_id": model_run_id})
    expected = int(validation["records"])
    if forecast_count != expected or recommendation_count != expected:
        raise ValueError("Persisted demand run is incomplete and cannot be activated")

    now = utc_now()
    await db[DEMAND_MODEL_RUN_COLLECTION].update_one(
        {"_id": model_run_id, "status": "staging"},
        {"$set": {"status": "completed", "validation": validation, "activated_at": now}},
    )
    run = await db[DEMAND_MODEL_RUN_COLLECTION].find_one({"_id": model_run_id})
    pointer_metadata = {
        "model_run_id": model_run_id,
        "model_version": (run or {}).get("model_version") or MODEL_VERSION,
        "run_type": (run or {}).get("run_type"),
        "horizon_days": int((run or {}).get("horizon_days") or validation.get("days") or 0),
        "source_requested": (run or {}).get("source_requested"),
        "effective_source": (run or {}).get("effective_source") or (run or {}).get("source_requested"),
        "fallback_used": bool((run or {}).get("fallback_used", False)),
        "request_fingerprint": (run or {}).get("request_fingerprint"),
        "generated_at": (run or {}).get("generated_at") or (run or {}).get("created_at"),
        "activated_at": now,
    }
    # One-document replacement is the visibility boundary. Readers never query
    # staging rows and switch from the previous complete run in one write.
    await db[DEMAND_ACTIVE_RUN_COLLECTION].update_one(
        {"_id": DEMAND_ACTIVE_RUN_POINTER_ID},
        {"$set": pointer_metadata},
        upsert=True,
    )


async def _mark_run_failed(model_run_id: ObjectId, exc: Exception) -> None:
    await _db()[DEMAND_MODEL_RUN_COLLECTION].update_one(
        {"_id": model_run_id},
        {"$set": {"status": "failed", "error": str(exc), "failed_at": utc_now()}},
    )


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


def _forecast_start_from_metrics(metrics: dict[str, Any]) -> datetime:
    dataset_end = (metrics.get("dataset") or {}).get("end")
    if not dataset_end:
        raise ValueError("Demand artifact metrics do not declare the dataset end date")
    return parse_forecast_date(dataset_end) + timedelta(days=1)


def _current_forecast_start(now: datetime | None = None) -> datetime:
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        local_reference = reference.replace(tzinfo=COLOMBO_TIMEZONE)
    else:
        local_reference = reference.astimezone(COLOMBO_TIMEZONE)
    return datetime(local_reference.year, local_reference.month, local_reference.day, tzinfo=timezone.utc)


def _forecast_window(frame: pd.DataFrame, days: int, expected_start: datetime) -> pd.DataFrame:
    result = frame.copy()
    result["ds"] = pd.to_datetime(result["ds"], errors="coerce")
    result = result.dropna(subset=["ds"])
    available_dates = sorted(result["ds"].dt.date.unique())
    selected_dates = available_dates[:days]
    selected = result[result["ds"].dt.date.isin(selected_dates)].copy()
    date_map = {
        source_date: expected_start.replace(tzinfo=None) + timedelta(days=index)
        for index, source_date in enumerate(selected_dates)
    }
    selected["ds"] = selected["ds"].dt.date.map(date_map)
    return selected


def _standardize_forecasts(frame: pd.DataFrame, days: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        record = standardize_forecast_record(row, horizon_days=days)
        record["lower_bound"] = safe_float(row.get("yhat_lower"), default=None) if row.get("yhat_lower") is not None else None
        record["upper_bound"] = safe_float(row.get("yhat_upper"), default=None) if row.get("yhat_upper") is not None else None
        records.append(record)
    return records


def _planning_from_forecasts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for record in records:
        level = normalize_demand_level(record["predicted_demand"])
        result.append({
            "zone_id": record["zone_id"],
            "forecast_date": record["forecast_date"],
            "predicted_demand": record["predicted_demand"],
            "demand_level": level,
            "estimated_required_vehicles": estimate_required_vehicles(record["predicted_demand"]),
            "recommended_action": recommended_action_from_demand_level(level),
        })
    return result


def _add_forecast_planning_fields(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    predicted_demand = safe_float(result.get("predicted_demand"))
    level = normalize_demand_level(predicted_demand)
    result.update({
        "predicted_demand": predicted_demand,
        "demand_level": level,
        "estimated_required_vehicles": estimate_required_vehicles(predicted_demand),
        "recommended_action": recommended_action_from_demand_level(level),
    })
    return result


async def import_artifact_forecasts_to_database(current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    artifacts = load_demand_artifacts()
    zones_df = load_zone_metadata_csv()
    forecast_df = load_future_forecast_csv()
    expected_start = _current_forecast_start()
    unique_dates = sorted(pd.to_datetime(forecast_df["ds"]).dt.date.unique())
    forecast_df = _forecast_window(forecast_df, len(unique_dates), expected_start)

    for row in zones_df.to_dict(orient="records"):
        await _upsert_zone(row)

    forecast_records = _standardize_forecasts(forecast_df, len(unique_dates))
    planning_records = _planning_from_forecasts(forecast_records)
    validation = _validate_complete_run(
        forecast_records,
        planning_records,
        expected_zone_ids=set(zones_df["zone_id"].astype(str)),
        expected_days=len(unique_dates),
        expected_start=expected_start,
    )
    forecast_dates = [record["forecast_date"] for record in forecast_records]
    request_fingerprint = _request_fingerprint(MODEL_VERSION, "artifact", len(unique_dates), expected_start)
    model_run_id = await _create_model_run(
        "artifact_import",
        records_generated=len(forecast_records),
        zones_count=len(zones_df),
        forecast_dates=forecast_dates,
        current_user=current_user,
        horizon_days=len(unique_dates),
        source_requested="artifact",
        effective_source="artifact",
        fallback_used=False,
        request_fingerprint=request_fingerprint,
    )

    try:
        await _persist_forecast_run(forecast_records, planning_records, model_run_id)
        await _activate_complete_run(model_run_id, validation)
    except Exception as exc:
        await _mark_run_failed(model_run_id, exc)
        raise

    alerts_created = 0
    for record in planning_records:
        if await _create_demand_alert_if_needed(record):
            alerts_created += 1

    return {
        "zones_imported": len(zones_df),
        "forecast_records": len(forecast_records),
        "planning_records": len(planning_records),
        "alerts_created": alerts_created,
        "model_run_id": str(model_run_id),
        "model_version": MODEL_VERSION,
        "active_run": await _active_run_metadata(),
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
    items = [enrich_zone_record(row) for row in serialize_mongo_list(await cursor.to_list(length=limit))]
    return build_pagination_response(items, total, page, limit)


async def list_forecasts(
    zone_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    demand_level: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    active_run_id = await get_active_run_id()
    if active_run_id is None:
        return {**build_pagination_response([], 0, page, limit), "active_run": None}
    query: dict[str, Any] = {"model_run_id": active_run_id}
    if zone_id:
        query["zone_id"] = operational_zone_id(zone_id)
    date_filter = _date_range_filter(start_date, end_date)
    if date_filter:
        query["forecast_date"] = date_filter
    if demand_level:
        if demand_level not in {"low", "medium", "high", "very_high"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid demand level")
        thresholds = {
            "low": {"$lte": 12},
            "medium": {"$gt": 12, "$lte": 18},
            "high": {"$gt": 18, "$lte": 25},
            "very_high": {"$gt": 25},
        }
        query["predicted_demand"] = thresholds[demand_level]

    collection = _db()[DEMAND_FORECAST_COLLECTION]
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("forecast_date", 1).skip(calculate_skip(page, limit)).limit(limit)
    items = [enrich_zone_record(row) for row in serialize_mongo_list(await cursor.to_list(length=limit))]
    return {**build_pagination_response(items, total, page, limit), "active_run": await _active_run_metadata()}


async def get_zone_forecast(zone_id: str, days: int = 30) -> dict[str, Any]:
    days = min(max(days, 1), 365)
    operational = operational_zone_id(zone_id)
    active_run_id = await get_active_run_id()
    query = {"model_run_id": active_run_id, "zone_id": operational} if active_run_id else {"_id": {"$exists": False}}
    cursor = _db()[DEMAND_FORECAST_COLLECTION].find(query).sort("forecast_date", 1).limit(days)
    items = [enrich_zone_record(row) for row in serialize_mongo_list(await cursor.to_list(length=days))]
    return {
        "zone_id": operational,
        "days": days,
        "data_context": DATA_CONTEXT,
        "items": items,
        "active_run": await _active_run_metadata(),
    }


async def get_fleet_planning_recommendations(
    zone_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    demand_level: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    active_run_id = await get_active_run_id()
    if active_run_id is None:
        return {**build_pagination_response([], 0, page, limit), "active_run": None}
    query: dict[str, Any] = {"model_run_id": active_run_id}
    if zone_id:
        query["zone_id"] = operational_zone_id(zone_id)
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
    items = [enrich_zone_record(row) for row in serialize_mongo_list(await cursor.to_list(length=limit))]
    return {**build_pagination_response(items, total, page, limit), "active_run": await _active_run_metadata()}


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
    artifacts = load_demand_artifacts()
    models = artifacts.models
    adjacency = artifacts.adjacency
    alpha = artifacts.spatial_alpha
    forecast_start = _current_forecast_start().replace(tzinfo=None)
    if not models:
        raise DemandArtifactUnavailableError("Demand forecasting model bundle has no Prophet models", {"artifact_path": str(DEMAND_ARTIFACT_DIR)})

    baseline_rows: list[pd.DataFrame] = []
    for zone, model in models.items():
        target_dates = pd.DataFrame({"ds": pd.date_range(start=forecast_start, periods=days, freq="D")})
        future_forecast = model.predict(target_dates).copy()
        future_forecast["zone_id"] = zone
        future_forecast["yhat"] = future_forecast["yhat"].clip(lower=0)
        baseline_rows.append(future_forecast[["zone_id", "ds", "yhat"]])

    return _apply_graph_enhancement_to_forecast(pd.concat(baseline_rows, ignore_index=True), adjacency, alpha=alpha)


async def refresh_forecast_from_model(days: int = 30, save_to_database: bool = True, source: str = "model", current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    if days not in APPROVED_REFRESH_HORIZONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Demand forecast horizon must be exactly 7, 14, or 30 days",
        )
    artifacts = load_demand_artifacts()
    expected_start = _current_forecast_start()
    request_fingerprint = _request_fingerprint(MODEL_VERSION, source, days, expected_start)
    if save_to_database:
        reusable_run = await _reusable_active_run(request_fingerprint, source)
        if reusable_run:
            active = _run_metadata(reusable_run)
            return {
                "source_requested": source,
                "fallback_used": False,
                "fallback_reason": None,
                "forecast_records": int(reusable_run.get("records_generated") or 0),
                "planning_records": int(reusable_run.get("records_generated") or 0),
                "alerts_created": 0,
                "model_run_id": active["model_run_id"],
                "model_version": MODEL_VERSION,
                "request_fingerprint": request_fingerprint,
                "reused_active_run": True,
                "active_run": active,
                "planning_window": active["planning_window"],
                "items": [],
                "data_context": DATA_CONTEXT,
            }

    expected_zones = set(artifacts.zone_metadata["zone_id"].astype(str))
    fallback_used = False
    fallback_reason = None
    if source == "model":
        try:
            forecast_df = _forecast_from_model_bundle(days)
        except Exception as exc:
            fallback_used = True
            fallback_reason = str(exc)
            forecast_df = _forecast_window(load_future_forecast_csv(), days, expected_start)
    else:
        forecast_df = _forecast_window(load_future_forecast_csv(), days, expected_start)

    effective_source = "artifact_fallback" if fallback_used else source
    effective_fingerprint = _request_fingerprint(MODEL_VERSION, effective_source, days, expected_start)
    if save_to_database and fallback_used:
        reusable_run = await _reusable_active_run(effective_fingerprint, effective_source)
        if reusable_run:
            active = _run_metadata(reusable_run)
            return {
                "source_requested": source,
                "effective_source": effective_source,
                "fallback_used": True,
                "fallback_reason": fallback_reason,
                "forecast_records": int(reusable_run.get("records_generated") or 0),
                "planning_records": int(reusable_run.get("records_generated") or 0),
                "alerts_created": 0,
                "model_run_id": active["model_run_id"],
                "model_version": MODEL_VERSION,
                "request_fingerprint": effective_fingerprint,
                "reused_active_run": True,
                "active_run": active,
                "planning_window": active["planning_window"],
                "items": [],
                "data_context": DATA_CONTEXT,
            }

    available_days = pd.to_datetime(forecast_df["ds"], errors="coerce").dt.date.nunique()
    if available_days != days:
        raise DemandArtifactUnavailableError(
            "The approved forecast horizon cannot satisfy the requested refresh",
            {"requested_days": days, "available_days": int(available_days), "model_version": MODEL_VERSION},
        )

    forecast_records = _standardize_forecasts(forecast_df, days)
    planning_records = _planning_from_forecasts(forecast_records)
    validation = _validate_complete_run(
        forecast_records,
        planning_records,
        expected_zone_ids=expected_zones,
        expected_days=days,
        expected_start=expected_start,
    )

    model_run_id = None
    alerts_created = 0
    if save_to_database:
        model_run_id = await _create_model_run(
            "model_forecast" if source == "model" and not fallback_used else "manual_refresh",
            records_generated=len(forecast_records),
            zones_count=len({record["zone_id"] for record in forecast_records}),
            forecast_dates=[record["forecast_date"] for record in forecast_records],
            current_user=current_user,
            horizon_days=days,
            source_requested=source,
            effective_source=effective_source,
            fallback_used=fallback_used,
            request_fingerprint=effective_fingerprint,
        )
        try:
            await _persist_forecast_run(forecast_records, planning_records, model_run_id)
            await _activate_complete_run(model_run_id, validation)
        except Exception as exc:
            await _mark_run_failed(model_run_id, exc)
            raise
        for record in planning_records:
            if await _create_demand_alert_if_needed(record):
                alerts_created += 1

    active = await _active_run_metadata() if model_run_id else None
    return {
        "source_requested": source,
        "effective_source": effective_source,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "forecast_records": len(forecast_records),
        "planning_records": len(planning_records),
        "alerts_created": alerts_created,
        "model_run_id": str(model_run_id) if model_run_id else None,
        "model_version": MODEL_VERSION,
        "request_fingerprint": effective_fingerprint,
        "reused_active_run": False,
        "active_run": active,
        "planning_window": active.get("planning_window") if active else None,
        "items": [enrich_zone_record(record) for record in forecast_records[:50]],
        "data_context": DATA_CONTEXT,
    }


async def get_demand_dashboard_summary() -> dict[str, Any]:
    db = _db()
    forecast_collection = db[DEMAND_FORECAST_COLLECTION]
    recommendation_collection = db[FLEET_RECOMMENDATION_COLLECTION]
    active_run_id = await get_active_run_id()
    active_filter = {"model_run_id": active_run_id} if active_run_id else {"_id": {"$exists": False}}
    first_forecast = await forecast_collection.find_one(active_filter, sort=[("forecast_date", 1)])
    latest = await forecast_collection.find_one(active_filter, sort=[("forecast_date", -1)])
    if first_forecast:
        window_start = first_forecast["forecast_date"]
        window_end = window_start + timedelta(days=7)
        next_7_query = {**active_filter, "forecast_date": {"$gte": window_start, "$lt": window_end}}
    else:
        next_7_query = active_filter

    from app.services.operational_demand_service import forecast_vs_actual
    comparison = await forecast_vs_actual(
        start_date=window_start.date() if first_forecast else None,
        end_date=(window_end - timedelta(days=1)).date() if first_forecast else None,
    )
    comparison_items = comparison["items"]
    high_zones = {row["operational_zone_id"] for row in comparison_items if row["demand_level"] == "high"}
    very_high_zones = {row["operational_zone_id"] for row in comparison_items if row["demand_level"] == "very_high"}
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
    comparison_totals: dict[str, float] = {}
    for row in comparison_items:
        comparison_totals[row["operational_zone_id"]] = comparison_totals.get(row["operational_zone_id"], 0.0) + row["predicted_demand"]
    active_top_zones = [
        enrich_zone_record({"zone_id": zone_id, "predicted_demand": total})
        for zone_id, total in sorted(comparison_totals.items(), key=lambda item: item[1], reverse=True)[:5]
    ]
    return {
        "total_zones": len(operational_zone_options()),
        "forecast_records": await forecast_collection.count_documents(active_filter),
        "high_demand_zones": len(high_zones),
        "very_high_demand_zones": len(very_high_zones),
        "total_predicted_demand_next_7_days": sum(row["predicted_demand"] for row in comparison_items) if comparison_items else (demand_sum[0]["total"] if demand_sum else 0),
        "total_required_vehicles_next_7_days": sum(row["estimated_required_vehicles"] for row in comparison_items) if comparison_items else (vehicles_sum[0]["total"] if vehicles_sum else 0),
        "top_demand_zones": active_top_zones or [
            enrich_zone_record({"zone_id": row["_id"], "predicted_demand": row["predicted_demand"]})
            for row in top_zones
        ],
        "latest_forecast_date": latest["forecast_date"].isoformat() if latest else None,
        "data_context": DATA_CONTEXT,
        "active_run": await _active_run_metadata(),
    }


async def get_latest_forecast_summary() -> dict[str, Any]:
    return await get_demand_dashboard_summary()


async def get_zone_adjacency_graph() -> dict[str, Any]:
    graph = load_zone_adjacency_graph()
    return {
        operational_zone_id(zone): [
            {**neighbor, "source_zone_id": neighbor.get("neighbor"), "neighbor": operational_zone_id(str(neighbor.get("neighbor")))}
            for neighbor in neighbors
        ]
        for zone, neighbors in graph.items()
    }


async def export_forecasts_as_csv(zone_id: str | None = None, start_date: str | None = None, end_date: str | None = None) -> str:
    active_run_id = await get_active_run_id()
    query: dict[str, Any] = {"model_run_id": active_run_id} if active_run_id else {"_id": {"$exists": False}}
    if zone_id:
        query["zone_id"] = operational_zone_id(zone_id)
    if start_date or end_date:
        query["forecast_date"] = {}
        if start_date:
            query["forecast_date"]["$gte"] = parse_forecast_date(start_date)
        if end_date:
            query["forecast_date"]["$lte"] = parse_forecast_date(end_date)
    cursor = _db()[DEMAND_FORECAST_COLLECTION].find(query).sort([("zone_id", 1), ("forecast_date", 1)])
    rows = [enrich_zone_record(row) for row in serialize_mongo_list(await cursor.to_list(length=10000))]
    output = StringIO()
    if not rows:
        pd.DataFrame(columns=["zone_id", "forecast_date", "predicted_demand", "model_type"]).to_csv(output, index=False)
    else:
        from app.utils.report_utils import safe_spreadsheet_value
        pd.DataFrame(rows).map(safe_spreadsheet_value).to_csv(output, index=False)
    return output.getvalue()
