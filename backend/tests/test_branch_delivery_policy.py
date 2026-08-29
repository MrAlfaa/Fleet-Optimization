from datetime import date

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.delivery_model import build_delivery_order_document
from app.schemas.delivery_schema import DeliveryOrderCreate
from app.services import route_optimizer_service
from app.utils.branch_operations import (
    FIRST_HALF,
    SECOND_HALF,
    apply_branch_origin,
    build_delivery_schedule,
    get_branch_profile,
)
from app.utils.route_utils import format_optimized_stop_order


def test_branch_origin_overrides_client_coordinates() -> None:
    branch = get_branch_profile()

    prepared = apply_branch_origin(
        {
            "pickup_latitude": 7.2906,
            "pickup_longitude": 80.6337,
            "pickup_address": "Client supplied pickup",
        }
    )

    assert prepared["pickup_latitude"] == branch["latitude"]
    assert prepared["pickup_longitude"] == branch["longitude"]
    assert prepared["pickup_address"] == branch["address"]
    assert prepared["pickup_source"] == "colombo_branch"


@pytest.mark.parametrize(
    ("period", "start_hour", "end_hour"),
    [(FIRST_HALF, 8, 12), (SECOND_HALF, 13, 17)],
)
def test_delivery_period_builds_colombo_schedule(period: str, start_hour: int, end_hour: int) -> None:
    schedule = build_delivery_schedule(date(2026, 8, 30), period)

    assert schedule["delivery_date"] == "2026-08-30"
    assert schedule["delivery_period"] == period
    assert schedule["delivery_window_start"].hour == start_hour
    assert schedule["delivery_window_end"].hour == end_hour
    assert schedule["delivery_window_start"].utcoffset() is not None


def test_delivery_create_requires_date_and_period_but_not_pickup_coordinates() -> None:
    payload = DeliveryOrderCreate(
        customer_name="Customer",
        drop_latitude=6.8649,
        drop_longitude=79.8997,
        delivery_date=date(2026, 8, 30),
        delivery_period=FIRST_HALF,
    )

    assert payload.pickup_latitude is None
    assert payload.pickup_longitude is None

    with pytest.raises(ValidationError):
        DeliveryOrderCreate(
            customer_name="Customer",
            drop_latitude=6.8649,
            drop_longitude=79.8997,
        )


def test_delivery_document_persists_branch_and_operational_window() -> None:
    branch = get_branch_profile()
    document = build_delivery_order_document(
        {
            "customer_name": "Customer",
            "drop_latitude": 6.8649,
            "drop_longitude": 79.8997,
            "delivery_date": date(2026, 8, 30),
            "delivery_period": SECOND_HALF,
        }
    )

    assert document["pickup_latitude"] == branch["latitude"]
    assert document["pickup_longitude"] == branch["longitude"]
    assert document["pickup_source"] == "colombo_branch"
    assert document["delivery_date"] == "2026-08-30"
    assert document["delivery_period"] == SECOND_HALF
    assert document["delivery_window_start"].hour == 13


def test_optimized_stop_order_keeps_delivery_identity_and_weight() -> None:
    points = [
        {"type": "depot", "order_id": None, "order_code": "DEPOT", "latitude": 6.9271, "longitude": 79.8612},
        {"type": "delivery", "order_id": "order-a", "order_code": "ORD-A", "latitude": 6.9, "longitude": 79.9, "parcel_weight": 4.5},
    ]

    result = format_optimized_stop_order(points, [0, 1, 0])

    assert result[1]["order_id"] == "order-a"
    assert result[1]["parcel_weight"] == 4.5


@pytest.mark.asyncio
async def test_route_rejects_deliveries_from_different_operational_periods(monkeypatch) -> None:
    orders = {
        "order-a": {
            "_id": "order-a",
            "order_code": "ORD-A",
            "delivery_status": "pending",
            "drop_latitude": 6.90,
            "drop_longitude": 79.90,
            "delivery_date": "2026-08-30",
            "delivery_period": FIRST_HALF,
        },
        "order-b": {
            "_id": "order-b",
            "order_code": "ORD-B",
            "delivery_status": "pending",
            "drop_latitude": 6.91,
            "drop_longitude": 79.91,
            "delivery_date": "2026-08-30",
            "delivery_period": SECOND_HALF,
        },
    }

    async def get_order(order_id: str):
        return orders[order_id]

    monkeypatch.setattr(route_optimizer_service, "get_raw_delivery_order_by_id", get_order)

    with pytest.raises(HTTPException) as exc:
        await route_optimizer_service.build_points_from_orders_or_stops(
            {
                "depot_latitude": 6.9271,
                "depot_longitude": 79.8612,
                "delivery_order_ids": ["order-a", "order-b"],
            }
        )

    assert exc.value.status_code == 409
    assert "same delivery date and period" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_route_records_the_selected_delivery_batch(monkeypatch) -> None:
    async def get_order(order_id: str):
        return {
            "_id": order_id,
            "order_code": order_id.upper(),
            "delivery_status": "pending",
            "drop_latitude": 6.90,
            "drop_longitude": 79.90,
            "delivery_date": "2026-08-30",
            "delivery_period": FIRST_HALF,
        }

    monkeypatch.setattr(route_optimizer_service, "get_raw_delivery_order_by_id", get_order)
    request_data = {
        "depot_latitude": 6.9271,
        "depot_longitude": 79.8612,
        "delivery_order_ids": ["order-a", "order-b"],
    }

    await route_optimizer_service.build_points_from_orders_or_stops(request_data)

    assert request_data["delivery_date"] == "2026-08-30"
    assert request_data["delivery_period"] == FIRST_HALF
