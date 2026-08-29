from __future__ import annotations

import argparse
import asyncio
import socket
import uuid

from app.core.database import close_mongo_connection, connect_to_mongo, get_database
from app.load_optimization.engine import optimize_batch
from app.models.delivery_model import DELIVERY_COLLECTION, safe_delivery_document
from app.models.load_optimization_model import LOAD_OPTIMIZATION_JOBS_COLLECTION
from app.services.load_optimization_service import (
    DEFAULT_VEHICLE_TYPE_CATALOG,
    claim_next_job,
    complete_job,
    fail_job,
    heartbeat_job,
)
from app.utils.object_id import validate_object_id


def default_worker_id() -> str:
    return f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


async def process_next_job(worker_id: str) -> bool:
    job = await claim_next_job(worker_id)
    if job is None:
        return False
    job_id = str(job["job_id"])
    try:
        database = get_database()
        if database is None:
            raise RuntimeError("MongoDB is unavailable")
        await heartbeat_job(job_id, worker_id, "loading_inputs", 10)
        order_ids = [validate_object_id(value) for value in job.get("order_ids", [])]
        rows = await database[DELIVERY_COLLECTION].find({
            "_id": {"$in": order_ids},
            "load_reservation_job_id": job_id,
            "load_planning_status": "reserved",
        }).to_list(length=len(order_ids))
        if len(rows) != len(order_ids):
            raise RuntimeError("Reserved parcel set changed before optimization")

        cancelled = await database[LOAD_OPTIMIZATION_JOBS_COLLECTION].find_one({"job_id": job_id, "status": "cancelled"})
        if cancelled:
            return True
        await heartbeat_job(job_id, worker_id, "spatial_clustering", 25)
        stop_heartbeat = asyncio.Event()

        async def keep_lease_alive() -> None:
            while True:
                try:
                    await asyncio.wait_for(stop_heartbeat.wait(), timeout=30)
                    return
                except asyncio.TimeoutError:
                    if not await heartbeat_job(job_id, worker_id, "optimizing_loads", 55):
                        return

        heartbeat_task = asyncio.create_task(keep_lease_alive())
        try:
            result = await asyncio.to_thread(
                optimize_batch,
                [safe_delivery_document(row) or {} for row in rows],
                [dict(item) for item in DEFAULT_VEHICLE_TYPE_CATALOG],
                seed=int(job.get("seed", 17)),
            )
        finally:
            stop_heartbeat.set()
            await heartbeat_task
        await heartbeat_job(job_id, worker_id, "persisting_plan", 90)
        await complete_job(job_id, worker_id, result)
    except Exception as exc:
        await fail_job(job_id, worker_id, f"{type(exc).__name__}: {exc}")
    return True


async def run(*, once: bool, poll_seconds: float, worker_id: str) -> None:
    await connect_to_mongo()
    try:
        while True:
            processed = await process_next_job(worker_id)
            if once:
                return
            if not processed:
                await asyncio.sleep(poll_seconds)
    finally:
        await close_mongo_connection()


def main() -> None:
    parser = argparse.ArgumentParser(description="FleetOpt isolated load optimization worker")
    parser.add_argument("--once", action="store_true", help="Process at most one queued job")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--worker-id", default=default_worker_id())
    args = parser.parse_args()
    asyncio.run(run(once=args.once, poll_seconds=max(args.poll_seconds, 0.2), worker_id=args.worker_id))


if __name__ == "__main__":
    main()
