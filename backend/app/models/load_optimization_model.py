from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.utils.object_id import serialize_mongo_document


LOAD_OPTIMIZATION_JOBS_COLLECTION = "load_optimization_jobs"
LOAD_OPTIMIZATION_PLANS_COLLECTION = "load_optimization_plans"
LOAD_VEHICLE_TYPE_CATALOG_COLLECTION = "load_vehicle_type_catalog"
PARCEL_CONSOLIDATIONS_COLLECTION = "parcel_consolidations"
LOAD_SEQUENCE_COUNTERS_COLLECTION = "load_sequence_counters"

PLAN_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"running", "cancelled", "failed"},
    "running": {"review_required", "cancelled", "failed"},
    "review_required": {"approved", "cancelled", "superseded", "failed"},
    "approved": {"superseded"},
    "failed": set(),
    "cancelled": set(),
    "superseded": set(),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _order_id(order: dict[str, Any]) -> str:
    return str(order.get("id") or order.get("_id") or order.get("order_code") or "")


def _fingerprint_order(order: dict[str, Any]) -> dict[str, Any]:
    profile = order.get("load_profile") or {}
    return {
        "id": _order_id(order),
        "delivery_status": order.get("delivery_status"),
        "parcel_weight": order.get("parcel_weight"),
        "priority": order.get("priority"),
        "drop_latitude": order.get("drop_latitude"),
        "drop_longitude": order.get("drop_longitude"),
        "load_profile": {
            key: profile.get(key)
            for key in (
                "length_cm",
                "width_cm",
                "height_cm",
                "volume_m3",
                "fragile",
                "stackable",
                "max_stack_weight_kg",
                "fixed_orientation",
                "do_not_tilt",
                "two_person_lift",
                "hazardous",
                "hazmat_class",
                "requires_refrigeration",
                "temp_min_celsius",
                "temp_max_celsius",
                "service_type",
            )
        },
    }


def build_batch_fingerprint(
    orders: Iterable[dict[str, Any]],
    delivery_date: str,
    delivery_period: str,
    *,
    seed: int,
) -> str:
    payload = {
        "branch": "colombo_central_branch",
        "delivery_date": delivery_date,
        "delivery_period": delivery_period,
        "seed": int(seed),
        "orders": sorted((_fingerprint_order(order) for order in orders), key=lambda item: item["id"]),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_consolidation_id(delivery_date: str, delivery_period: str, sequence: int) -> str:
    period_code = {"first_half": "1H", "second_half": "2H"}.get(delivery_period)
    if period_code is None:
        raise ValueError("Delivery period must be first_half or second_half")
    try:
        date_code = datetime.fromisoformat(delivery_date).strftime("%Y%m%d")
    except ValueError as exc:
        raise ValueError("Delivery date must use YYYY-MM-DD format") from exc
    if sequence < 1 or sequence > 999:
        raise ValueError("Consolidation sequence must be between 1 and 999")
    return f"PCID{date_code}{period_code}{sequence:03d}"


def build_consolidation_document(
    *,
    consolidation_id: str,
    sequence: int,
    orders: list[dict[str, Any]],
    snapshot: dict[str, Any],
    delivery_date: str,
    delivery_period: str,
    source_fingerprint: str,
    created_by: str,
) -> dict[str, Any]:
    now = _utc_now()
    region_by_parcel = {
        str(parcel_id): int(region.get("region_id", 0))
        for region in snapshot.get("regions", [])
        for parcel_id in region.get("parcel_ids", [])
    }
    parcel_points = []
    for order in sorted(orders, key=_order_id):
        parcel_id = _order_id(order)
        parcel_points.append({
            "parcel_id": parcel_id,
            "order_code": str(order.get("order_code") or parcel_id),
            "zone_id": order.get("zone_id") or order.get("operational_zone_id"),
            "drop_address": order.get("drop_address"),
            "latitude": float(order.get("drop_latitude") or 0),
            "longitude": float(order.get("drop_longitude") or 0),
            "region_id": region_by_parcel.get(parcel_id, 0),
        })
    return {
        "consolidation_id": consolidation_id,
        "sequence": int(sequence),
        "batch_key": f"colombo_central_branch:{delivery_date}:{delivery_period}",
        "delivery_date": delivery_date,
        "delivery_period": delivery_period,
        "status": "active",
        "source_fingerprint": source_fingerprint,
        "parcel_ids": sorted(_order_id(order) for order in orders),
        "parcel_points": parcel_points,
        "parcel_count": len(orders),
        "cluster_method": snapshot.get("cluster_method", "unknown"),
        "regions": list(snapshot.get("regions") or []),
        "active_plan_id": None,
        "created_by": str(created_by),
        "created_at": now,
        "updated_at": now,
    }


def build_optimization_job_document(
    *,
    orders: list[dict[str, Any]],
    delivery_date: str,
    delivery_period: str,
    seed: int,
    created_by: str,
    consolidation_id: str | None = None,
) -> dict[str, Any]:
    now = _utc_now()
    order_ids = sorted(_order_id(order) for order in orders)
    return {
        "job_id": f"LOADJOB-{now:%Y%m%d}-{uuid.uuid4().hex[:10].upper()}",
        "batch_key": f"colombo_central_branch:{delivery_date}:{delivery_period}",
        "delivery_date": delivery_date,
        "delivery_period": delivery_period,
        "order_ids": order_ids,
        "consolidation_id": consolidation_id,
        "input_fingerprint": build_batch_fingerprint(
            orders,
            delivery_date,
            delivery_period,
            seed=seed,
        ),
        "seed": int(seed),
        "status": "queued",
        "stage": "awaiting_worker",
        "progress_percent": 0,
        "attempt_count": 0,
        "created_by": str(created_by),
        "created_at": now,
        "updated_at": now,
        "lease_owner": None,
        "lease_expires_at": None,
        "heartbeat_at": None,
        "cancel_requested_at": None,
        "completed_at": None,
        "error": None,
    }


def validate_plan_transition(current: str, target: str) -> None:
    if target not in PLAN_TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid load plan transition from {current} to {target}")


def safe_load_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    return serialize_mongo_document(document)


async def ensure_load_optimization_indexes() -> None:
    db = get_database()
    if db is None:
        return
    try:
        jobs = db[LOAD_OPTIMIZATION_JOBS_COLLECTION]
        await jobs.create_index([("job_id", ASCENDING)], unique=True, name="unique_load_job_id")
        await jobs.create_index([("batch_key", ASCENDING), ("created_at", DESCENDING)], name="load_job_batch")
        await jobs.create_index([("input_fingerprint", ASCENDING), ("status", ASCENDING)], name="load_job_fingerprint")
        await jobs.create_index([("status", ASCENDING), ("lease_expires_at", ASCENDING)], name="load_job_worker_queue")

        plans = db[LOAD_OPTIMIZATION_PLANS_COLLECTION]
        await plans.create_index([("plan_id", ASCENDING)], unique=True, name="unique_load_plan_id")
        await plans.create_index([("batch_key", ASCENDING), ("revision", DESCENDING)], unique=True, name="load_plan_revision")
        await plans.create_index([("input_fingerprint", ASCENDING), ("status", ASCENDING)], name="load_plan_fingerprint")

        consolidations = db[PARCEL_CONSOLIDATIONS_COLLECTION]
        await consolidations.create_index([("consolidation_id", ASCENDING)], unique=True, name="unique_consolidation_id")
        await consolidations.create_index(
            [("source_fingerprint", ASCENDING), ("status", ASCENDING)],
            name="consolidation_source_fingerprint",
        )
        await consolidations.create_index(
            [("batch_key", ASCENDING), ("sequence", DESCENDING)],
            name="consolidation_batch_sequence",
        )
    except PyMongoError:
        return
