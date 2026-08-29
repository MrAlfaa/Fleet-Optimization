from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest
from bson import ObjectId

from app.models.demand_model import (
    DEMAND_ACTIVE_RUN_COLLECTION,
    DEMAND_FORECAST_COLLECTION,
    DEMAND_MODEL_RUN_COLLECTION,
    FLEET_RECOMMENDATION_COLLECTION,
)
from app.services import demand_forecasting_service, fleet_intelligence_service, operational_demand_service, report_service


UTC = timezone.utc


def _forecast(zone_id: str, day: int) -> dict:
    return {
        "zone_id": zone_id,
        "forecast_date": datetime(2027, 1, day, tzinfo=UTC),
        "predicted_demand": 14.0,
    }


def _recommendation(zone_id: str, day: int) -> dict:
    return {
        **_forecast(zone_id, day),
        "demand_level": "medium",
        "estimated_required_vehicles": 2,
        "recommended_action": "Monitor demand and maintain standard delivery capacity.",
    }


def test_complete_run_validation_rejects_a_missing_zone_date_pair() -> None:
    validate = getattr(demand_forecasting_service, "_validate_complete_run", None)
    assert validate is not None, "complete staged-run validation must be implemented"

    forecasts = [_forecast("LK_a", 1), _forecast("LK_b", 1), _forecast("LK_a", 2)]
    recommendations = [_recommendation("LK_a", 1), _recommendation("LK_b", 1), _recommendation("LK_a", 2)]

    with pytest.raises(ValueError, match="complete"):
        validate(
            forecasts,
            recommendations,
            expected_zone_ids={"LK_a", "LK_b"},
            expected_days=2,
            expected_start=datetime(2027, 1, 1, tzinfo=UTC),
        )


def test_complete_run_validation_accepts_every_zone_for_every_day() -> None:
    validate = getattr(demand_forecasting_service, "_validate_complete_run", None)
    assert validate is not None, "complete staged-run validation must be implemented"

    forecasts = [_forecast(zone, day) for day in (1, 2) for zone in ("LK_a", "LK_b")]
    recommendations = [_recommendation(zone, day) for day in (1, 2) for zone in ("LK_a", "LK_b")]

    summary = validate(
        forecasts,
        recommendations,
        expected_zone_ids={"LK_a", "LK_b"},
        expected_days=2,
        expected_start=datetime(2027, 1, 1, tzinfo=UTC),
    )

    assert summary["records"] == 4
    assert summary["zones"] == 2
    assert summary["days"] == 2


def test_comparison_item_uses_frozen_operational_contract() -> None:
    build_item = getattr(operational_demand_service, "_comparison_item", None)
    assert build_item is not None, "comparison response builder must be implemented"

    item = build_item(
        {
            "zone_id": "LK_colombo_central",
            "forecast_date": datetime(2027, 1, 1, tzinfo=UTC),
            "predicted_demand": 20.0,
            "baseline_prophet_forecast": 19.0,
            "lower_bound": 15.0,
            "upper_bound": 25.0,
            "model_version": "fleetopt-demand-synthetic-v1",
            "created_at": datetime(2026, 12, 31, tzinfo=UTC),
        },
        actual_orders=18,
    )

    assert item["predicted_demand"] == 20.0
    assert item["final_predicted_demand"] == 20.0
    assert item["variance_orders"] == 2.0
    assert item["variance_percentage"] == pytest.approx(11.11)
    assert item["baseline_forecast"] == 19.0
    assert item["model_version"] == "fleetopt-demand-synthetic-v1"
    assert not ({"raw_mapped_forecast", "calibration_status", "calibration_factor", "calibrated_forecast"} & set(item))


def test_comparison_item_keeps_variance_nullable_without_actuals() -> None:
    build_item = getattr(operational_demand_service, "_comparison_item", None)
    assert build_item is not None, "comparison response builder must be implemented"

    item = build_item(_forecast("LK_colombo_central", 1), actual_orders=None)

    assert item["local_actual_demand"] is None
    assert item["variance_orders"] is None
    assert item["variance_percentage"] is None


class _Collection:
    def __init__(self, *, count: int = 0, rows: list[dict] | None = None):
        self.count = count
        self.rows = rows or []
        self.updates: list[tuple[dict, dict, bool]] = []
        self.last_query: dict | None = None

    async def count_documents(self, query: dict) -> int:
        self.last_query = query
        return self.count

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        self.last_query = query
        self.updates.append((query, update, upsert))

    async def find_one(self, query: dict, sort=None):
        self.last_query = query
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                return row
        return None

    def find(self, query: dict):
        self.last_query = query
        return self

    def sort(self, *args, **kwargs):
        return self

    def skip(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def to_list(self, length: int):
        return self.rows[:length]


@pytest.mark.asyncio
async def test_pointer_activates_only_after_both_staged_collections_are_complete(monkeypatch) -> None:
    run_id = ObjectId()
    forecasts = _Collection(count=30)
    recommendations = _Collection(count=30)
    runs = _Collection()
    pointer = _Collection()
    database = {
        DEMAND_FORECAST_COLLECTION: forecasts,
        FLEET_RECOMMENDATION_COLLECTION: recommendations,
        DEMAND_MODEL_RUN_COLLECTION: runs,
        DEMAND_ACTIVE_RUN_COLLECTION: pointer,
    }
    monkeypatch.setattr(demand_forecasting_service, "_db", lambda: database)

    await demand_forecasting_service._activate_complete_run(run_id, {"records": 30})

    assert runs.updates[0][1]["$set"]["status"] == "completed"
    assert pointer.updates[0][1]["$set"]["model_run_id"] == run_id
    assert pointer.updates[0][2] is True


@pytest.mark.asyncio
async def test_incomplete_staged_run_does_not_replace_active_pointer(monkeypatch) -> None:
    database = {
        DEMAND_FORECAST_COLLECTION: _Collection(count=29),
        FLEET_RECOMMENDATION_COLLECTION: _Collection(count=30),
        DEMAND_MODEL_RUN_COLLECTION: _Collection(),
        DEMAND_ACTIVE_RUN_COLLECTION: _Collection(),
    }
    monkeypatch.setattr(demand_forecasting_service, "_db", lambda: database)

    with pytest.raises(ValueError, match="incomplete"):
        await demand_forecasting_service._activate_complete_run(ObjectId(), {"records": 30})

    assert database[DEMAND_ACTIVE_RUN_COLLECTION].updates == []


def test_artifact_window_keeps_all_fifteen_zones_per_selected_day() -> None:
    zones = [f"LK_zone_{index}" for index in range(15)]
    frame = pd.DataFrame(
        [
            {"zone_id": zone, "ds": f"2027-01-0{day}", "predicted_demand": 10}
            for zone in zones
            for day in (1, 2, 3)
        ]
    )

    selected = demand_forecasting_service._forecast_window(frame, 2, datetime(2027, 1, 1, tzinfo=UTC))

    assert len(selected) == 30
    assert selected["zone_id"].nunique() == 15
    assert selected["ds"].min().date().isoformat() == "2027-01-01"


def test_operational_forecast_start_uses_current_colombo_business_date() -> None:
    start = demand_forecasting_service._current_forecast_start(
        datetime(2026, 8, 27, 20, 15, tzinfo=UTC)
    )

    assert start.isoformat() == "2026-08-28T00:00:00+00:00"


@pytest.mark.asyncio
async def test_export_filters_out_legacy_and_inactive_runs(monkeypatch) -> None:
    active_run_id = ObjectId()
    forecasts = _Collection()
    monkeypatch.setattr(demand_forecasting_service, "_db", lambda: {DEMAND_FORECAST_COLLECTION: forecasts})

    async def active_id():
        return active_run_id

    monkeypatch.setattr(demand_forecasting_service, "get_active_run_id", active_id)

    await demand_forecasting_service.export_forecasts_as_csv()

    assert forecasts.last_query == {"model_run_id": active_run_id}


@pytest.mark.asyncio
async def test_fleet_readiness_date_lookup_uses_active_run_pointer(monkeypatch) -> None:
    active_run_id = ObjectId()
    recommendations = _Collection(rows=[{
        "model_run_id": active_run_id,
        "forecast_date": datetime(2027, 1, 1, tzinfo=UTC),
    }])
    monkeypatch.setattr(
        fleet_intelligence_service,
        "_db",
        lambda: {
            DEMAND_ACTIVE_RUN_COLLECTION: _Collection(rows=[{"_id": "active", "model_run_id": active_run_id}]),
            FLEET_RECOMMENDATION_COLLECTION: recommendations,
        },
    )

    selected = await fleet_intelligence_service._selected_forecast_date()

    assert selected.isoformat() == "2027-01-01"
    assert recommendations.last_query == {"model_run_id": active_run_id}


@pytest.mark.asyncio
async def test_model_status_exposes_version_quality_degraded_and_active_run(monkeypatch) -> None:
    monkeypatch.setattr(
        demand_forecasting_service,
        "get_demand_artifact_status",
        lambda load_model=True: {
            "model_version": "fleetopt-demand-synthetic-v1",
            "quality_passed": True,
            "degraded": False,
        },
    )

    async def active_metadata():
        return {"model_run_id": "run-1", "model_version": "fleetopt-demand-synthetic-v1"}

    monkeypatch.setattr(demand_forecasting_service, "_active_run_metadata", active_metadata)

    status = await demand_forecasting_service.get_model_status()

    assert status["model_version"] == "fleetopt-demand-synthetic-v1"
    assert status["quality_passed"] is True
    assert status["degraded"] is False
    assert status["operational_state"] == "ready"
    assert status["active_run"]["model_run_id"] == "run-1"


@pytest.mark.asyncio
async def test_demand_report_query_is_limited_to_the_active_run(monkeypatch) -> None:
    active_run_id = ObjectId()

    async def active_id():
        return active_run_id

    monkeypatch.setattr(demand_forecasting_service, "get_active_run_id", active_id)
    query = await report_service._report_collection_query(
        "Demand",
        datetime(2027, 1, 1, tzinfo=UTC),
        datetime(2027, 1, 7, tzinfo=UTC),
    )

    assert query == {
        "model_run_id": active_run_id,
        "forecast_date": {
            "$gte": datetime(2027, 1, 1, tzinfo=UTC),
            "$lte": datetime(2027, 1, 7, tzinfo=UTC),
        },
    }
