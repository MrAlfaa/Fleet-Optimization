from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from app.models.demand_model import DEMAND_ACTIVE_RUN_COLLECTION, DEMAND_ACTIVE_RUN_POINTER_ID
from app.services import fleet_intelligence_service


UTC = timezone.utc


class _Collection:
    def __init__(self, row: dict | None = None):
        self.row = row
        self.last_query: dict | None = None
        self.last_sort = None

    async def find_one(self, query: dict, sort=None):
        self.last_query = query
        self.last_sort = sort
        return self.row


class _MissingCollection(_Collection):
    async def find_one(self, query: dict, sort=None):
        self.last_query = query
        self.last_sort = sort
        return None


@pytest.mark.asyncio
async def test_default_readiness_date_uses_first_day_of_active_forecast_window(monkeypatch) -> None:
    run_id = ObjectId()
    pointer = _Collection({"_id": DEMAND_ACTIVE_RUN_POINTER_ID, "model_run_id": run_id})
    recommendations = _Collection({
        "model_run_id": run_id,
        "forecast_date": datetime(2027, 1, 1, tzinfo=UTC),
    })
    monkeypatch.setattr(
        fleet_intelligence_service,
        "_db",
        lambda: {
            DEMAND_ACTIVE_RUN_COLLECTION: pointer,
            fleet_intelligence_service.FLEET_RECOMMENDATION_COLLECTION: recommendations,
        },
    )

    selected = await fleet_intelligence_service._selected_forecast_date()

    assert selected.isoformat() == "2027-01-01"
    assert recommendations.last_query == {"model_run_id": run_id}
    assert recommendations.last_sort == [("forecast_date", 1)]


@pytest.mark.asyncio
async def test_readiness_rejects_date_outside_active_forecast_window(monkeypatch) -> None:
    run_id = ObjectId()
    pointer = _Collection({"_id": DEMAND_ACTIVE_RUN_POINTER_ID, "model_run_id": run_id})
    recommendations = _MissingCollection()
    monkeypatch.setattr(
        fleet_intelligence_service,
        "_db",
        lambda: {
            DEMAND_ACTIVE_RUN_COLLECTION: pointer,
            fleet_intelligence_service.FLEET_RECOMMENDATION_COLLECTION: recommendations,
        },
    )

    with pytest.raises(Exception) as captured:
        await fleet_intelligence_service._selected_forecast_date("2026-08-28")

    assert getattr(captured.value, "status_code", None) == 400
    assert "active forecast window" in str(getattr(captured.value, "detail", "")).lower()


@pytest.mark.asyncio
async def test_readiness_rejects_missing_active_forecast_instead_of_reporting_zero_demand(monkeypatch) -> None:
    monkeypatch.setattr(
        fleet_intelligence_service,
        "_db",
        lambda: {DEMAND_ACTIVE_RUN_COLLECTION: _MissingCollection()},
    )

    with pytest.raises(Exception) as captured:
        await fleet_intelligence_service._selected_forecast_date()

    assert getattr(captured.value, "status_code", None) == 503
    assert "active demand forecast" in str(getattr(captured.value, "detail", "")).lower()


@pytest.mark.asyncio
async def test_pre_resolved_run_id_avoids_rereading_active_pointer(monkeypatch) -> None:
    run_id = ObjectId()
    pointer = _MissingCollection()
    recommendations = _Collection({
        "model_run_id": run_id,
        "forecast_date": datetime(2027, 1, 1, tzinfo=UTC),
    })
    monkeypatch.setattr(
        fleet_intelligence_service,
        "_db",
        lambda: {
            DEMAND_ACTIVE_RUN_COLLECTION: pointer,
            fleet_intelligence_service.FLEET_RECOMMENDATION_COLLECTION: recommendations,
        },
    )

    selected = await fleet_intelligence_service._selected_forecast_date(active_run_id=run_id)

    assert selected.isoformat() == "2027-01-01"
    assert pointer.last_query is None
