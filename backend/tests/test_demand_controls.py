from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest
from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from pydantic import ValidationError

from app.models.demand_model import (
    DEMAND_ACTIVE_RUN_COLLECTION,
    DEMAND_FORECAST_COLLECTION,
    DEMAND_MODEL_RUN_COLLECTION,
    build_demand_model_run_document,
)
from app.schemas.demand_schema import DemandForecastRefreshRequest
from app.services import demand_forecasting_service
from app.services.demand_artifact_registry import MODEL_VERSION


UTC = timezone.utc
FORECAST_START = datetime(2027, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize("days", [7, 14, 30])
def test_refresh_request_accepts_only_approved_horizons(days: int) -> None:
    request = DemandForecastRefreshRequest(days=days)

    assert request.days == days
    assert request.source == "model"
    assert request.save_to_database is True


@pytest.mark.parametrize("days", [1, 13, 15, 29, 31, 365])
def test_refresh_request_rejects_unapproved_horizons(days: int) -> None:
    with pytest.raises(ValidationError):
        DemandForecastRefreshRequest(days=days)


@pytest.mark.parametrize(
    ("field", "value"),
    [("source", "artifact"), ("save_to_database", False)],
)
def test_refresh_request_keeps_model_source_and_database_persistence(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        DemandForecastRefreshRequest(**{field: value})


def test_model_run_document_persists_request_identity_metadata() -> None:
    document = build_demand_model_run_document(
        {
            "run_type": "model_forecast",
            "model_name": MODEL_VERSION,
            "artifact_source": "private/artifact/path",
            "request_fingerprint": "fingerprint-30",
            "horizon_days": 30,
            "source_requested": "model",
        }
    )

    assert document["request_fingerprint"] == "fingerprint-30"
    assert document["horizon_days"] == 30
    assert document["source_requested"] == "model"


def test_request_fingerprint_is_deterministic_and_horizon_sensitive() -> None:
    first = demand_forecasting_service._request_fingerprint(MODEL_VERSION, "model", 30, FORECAST_START)
    repeated = demand_forecasting_service._request_fingerprint(MODEL_VERSION, "model", 30, FORECAST_START)
    shorter = demand_forecasting_service._request_fingerprint(MODEL_VERSION, "model", 14, FORECAST_START)

    assert first == repeated
    assert first != shorter
    assert len(first) == 64


class _Cursor:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.sort_args = None
        self.limit_value = None

    def sort(self, *args):
        self.sort_args = args
        return self

    def limit(self, value: int):
        self.limit_value = value
        return self

    def skip(self, value: int):
        self.rows = self.rows[value:]
        return self

    async def to_list(self, length: int):
        return self.rows[:length]


class _Collection:
    def __init__(self, rows: list[dict] | None = None):
        self.rows = rows or []
        self.last_query = None
        self.cursor = None

    async def find_one(self, query: dict, sort=None):
        self.last_query = query
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                return row
        return None

    async def count_documents(self, query: dict):
        self.last_query = query
        return len(self.rows)

    def find(self, query: dict):
        self.last_query = query
        self.cursor = _Cursor(self.rows)
        return self.cursor


def _completed_run(run_id: ObjectId, *, horizon_days: int = 30, fingerprint: str = "fingerprint-30") -> dict:
    return {
        "_id": run_id,
        "run_type": "model_forecast",
        "model_name": MODEL_VERSION,
        "model_version": MODEL_VERSION,
        "status": "completed",
        "request_fingerprint": fingerprint,
        "horizon_days": horizon_days,
        "source_requested": "model",
        "effective_source": "model",
        "fallback_used": False,
        "forecast_start_date": FORECAST_START,
        "forecast_end_date": datetime(2027, 1, horizon_days, tzinfo=UTC),
        "zones_count": 15,
        "records_generated": horizon_days * 15,
        "created_at": datetime(2026, 12, 31, 8, tzinfo=UTC),
        "activated_at": datetime(2026, 12, 31, 9, tzinfo=UTC),
        "artifact_source": "C:/private/model.joblib",
        "metrics_snapshot": {"dataset": {"end": "2026-12-31"}},
    }


@pytest.mark.asyncio
async def test_active_run_metadata_serializes_operational_fields_and_planning_window(monkeypatch) -> None:
    run_id = ObjectId()
    run = _completed_run(run_id)
    database = {
        DEMAND_ACTIVE_RUN_COLLECTION: _Collection([{"_id": "active", "model_run_id": run_id}]),
        DEMAND_MODEL_RUN_COLLECTION: _Collection([run]),
    }
    monkeypatch.setattr(demand_forecasting_service, "_db", lambda: database)

    metadata = await demand_forecasting_service._active_run_metadata()

    assert metadata == {
        "model_run_id": str(run_id),
        "run_type": "model_forecast",
        "model_version": MODEL_VERSION,
        "horizon_days": 30,
        "source_requested": "model",
        "effective_source": "model",
        "fallback_used": False,
        "request_fingerprint": "fingerprint-30",
        "forecast_start_date": "2027-01-01T00:00:00+00:00",
        "forecast_end_date": "2027-01-30T00:00:00+00:00",
        "zones_count": 15,
        "records_generated": 450,
        "generated_at": "2026-12-31T08:00:00+00:00",
        "activated_at": "2026-12-31T09:00:00+00:00",
        "planning_window": {
            "basis": "colombo_business_date",
            "dataset_end_date": "2026-12-31",
            "forecast_start_date": "2027-01-01T00:00:00+00:00",
            "forecast_end_date": "2027-01-30T00:00:00+00:00",
            "horizon_days": 30,
        },
    }


@pytest.mark.asyncio
async def test_run_history_scopes_statuses_and_sanitizes_artifact_paths(monkeypatch) -> None:
    run = _completed_run(ObjectId())
    runs = _Collection([run])
    monkeypatch.setattr(demand_forecasting_service, "_db", lambda: {DEMAND_MODEL_RUN_COLLECTION: runs})
    monkeypatch.setattr(
        demand_forecasting_service,
        "load_demand_metrics",
        lambda: {"dataset": {"end": "2026-12-31"}},
    )

    result = await demand_forecasting_service.list_demand_runs(limit=12)

    assert runs.last_query == {
        "status": {"$in": ["completed", "failed"]},
        "model_version": MODEL_VERSION,
        "metrics_snapshot.dataset.end": "2026-12-31",
    }
    assert runs.cursor.limit_value == 12
    assert result["items"][0]["request_fingerprint"] == "fingerprint-30"
    assert "artifact_source" not in result["items"][0]
    assert "metrics_snapshot" not in result["items"][0]
    assert "C:/private" not in str(result)


@pytest.mark.asyncio
async def test_run_history_detail_returns_only_selected_completed_run_rows(monkeypatch) -> None:
    run_id = ObjectId()
    run = _completed_run(run_id)
    runs = _Collection([run])
    forecasts = _Collection([
        {
            "_id": ObjectId(),
            "model_run_id": run_id,
            "zone_id": "LK_colombo_central",
            "forecast_date": FORECAST_START,
            "predicted_demand": 20,
        }
    ])
    database = {
        DEMAND_MODEL_RUN_COLLECTION: runs,
        DEMAND_FORECAST_COLLECTION: forecasts,
    }
    monkeypatch.setattr(demand_forecasting_service, "_db", lambda: database)
    monkeypatch.setattr(demand_forecasting_service, "load_demand_metrics", lambda: {})

    result = await demand_forecasting_service.get_demand_run_forecasts(str(run_id), page=1, limit=50)

    assert result["run"]["model_run_id"] == str(run_id)
    assert result["total"] == 1
    assert result["items"][0]["zone_id"] == "LK_colombo_central"
    assert result["items"][0]["demand_level"] == "high"
    assert result["items"][0]["estimated_required_vehicles"] == 2
    assert forecasts.last_query == {"model_run_id": run_id}


@pytest.mark.asyncio
async def test_same_request_reuses_active_completed_run_without_generation_or_writes(monkeypatch) -> None:
    fingerprint = demand_forecasting_service._request_fingerprint(MODEL_VERSION, "model", 30, FORECAST_START)
    run_id = ObjectId()
    run = _completed_run(run_id, fingerprint=fingerprint)
    database = {
        DEMAND_ACTIVE_RUN_COLLECTION: _Collection([{"_id": "active", "model_run_id": run_id}]),
        DEMAND_MODEL_RUN_COLLECTION: _Collection([run]),
    }
    monkeypatch.setattr(demand_forecasting_service, "_db", lambda: database)
    monkeypatch.setattr(
        demand_forecasting_service,
        "load_demand_artifacts",
        lambda: SimpleNamespace(metrics={"dataset": {"end": "2026-12-31"}}),
    )
    monkeypatch.setattr(demand_forecasting_service, "_current_forecast_start", lambda: FORECAST_START)

    def unexpected_generation(days: int):
        raise AssertionError("model generation must not run for an identical active request")

    monkeypatch.setattr(demand_forecasting_service, "_forecast_from_model_bundle", unexpected_generation)

    result = await demand_forecasting_service.refresh_forecast_from_model(
        days=30,
        save_to_database=True,
        source="model",
    )

    assert result["reused_active_run"] is True
    assert result["model_run_id"] == str(run_id)
    assert result["alerts_created"] == 0


@pytest.mark.asyncio
async def test_fallback_run_is_not_reused_as_successful_model_inference(monkeypatch) -> None:
    run = _completed_run(ObjectId())
    run.update({"fallback_used": True, "effective_source": "artifact_fallback"})

    async def active_run():
        return run

    monkeypatch.setattr(demand_forecasting_service, "_active_run_document", active_run)

    assert await demand_forecasting_service._reusable_active_run(run["request_fingerprint"], "model") is None


@pytest.mark.asyncio
async def test_duplicate_staging_fingerprint_returns_forecast_in_progress(monkeypatch) -> None:
    class DuplicateCollection:
        async def insert_one(self, document: dict):
            raise DuplicateKeyError("duplicate staging request")

    monkeypatch.setattr(
        demand_forecasting_service,
        "_db",
        lambda: {DEMAND_MODEL_RUN_COLLECTION: DuplicateCollection()},
    )
    monkeypatch.setattr(demand_forecasting_service, "load_demand_metrics", lambda: {})

    with pytest.raises(HTTPException) as captured:
        await demand_forecasting_service._create_model_run(
            "model_forecast",
            records_generated=15,
            zones_count=15,
            forecast_dates=[FORECAST_START],
            current_user=None,
            horizon_days=7,
            source_requested="model",
            effective_source="model",
            fallback_used=False,
            request_fingerprint="same-request",
        )

    assert captured.value.status_code == 409
    assert "already in progress" in str(captured.value.detail).lower()


@pytest.mark.asyncio
async def test_different_horizon_does_not_reuse_active_run(monkeypatch) -> None:
    active_fingerprint = demand_forecasting_service._request_fingerprint(MODEL_VERSION, "model", 30, FORECAST_START)
    run_id = ObjectId()
    run = _completed_run(run_id, horizon_days=30, fingerprint=active_fingerprint)
    database = {
        DEMAND_ACTIVE_RUN_COLLECTION: _Collection([{"_id": "active", "model_run_id": run_id}]),
        DEMAND_MODEL_RUN_COLLECTION: _Collection([run]),
    }
    monkeypatch.setattr(demand_forecasting_service, "_db", lambda: database)
    monkeypatch.setattr(
        demand_forecasting_service,
        "load_demand_artifacts",
        lambda: SimpleNamespace(
            metrics={"dataset": {"end": "2026-12-31"}},
            zone_metadata=pd.DataFrame({"zone_id": ["LK_zone"]}),
        ),
    )
    monkeypatch.setattr(demand_forecasting_service, "_current_forecast_start", lambda: FORECAST_START)
    monkeypatch.setattr(
        demand_forecasting_service,
        "_forecast_from_model_bundle",
        lambda days: pd.DataFrame(
            [{"zone_id": "LK_zone", "ds": f"2027-01-{day:02d}", "yhat": 10.0} for day in range(1, days + 1)]
        ),
    )

    created_run_id = ObjectId()
    created: list[dict] = []

    async def create_run(*args, **kwargs):
        created.append(kwargs)
        return created_run_id

    persisted: list[ObjectId] = []
    activated: list[ObjectId] = []

    async def persist_run(forecasts, recommendations, model_run_id):
        persisted.append(model_run_id)

    async def activate_run(model_run_id, validation):
        activated.append(model_run_id)

    async def no_op(*args, **kwargs):
        return None

    async def active_metadata():
        return {"model_run_id": str(created_run_id), "horizon_days": 14}

    monkeypatch.setattr(demand_forecasting_service, "_create_model_run", create_run)
    monkeypatch.setattr(demand_forecasting_service, "_persist_forecast_run", persist_run)
    monkeypatch.setattr(demand_forecasting_service, "_activate_complete_run", activate_run)
    monkeypatch.setattr(demand_forecasting_service, "_create_demand_alert_if_needed", no_op)
    monkeypatch.setattr(demand_forecasting_service, "_active_run_metadata", active_metadata)

    result = await demand_forecasting_service.refresh_forecast_from_model(days=14, source="model")

    assert result["reused_active_run"] is False
    assert result["model_run_id"] == str(created_run_id)
    assert created[0]["horizon_days"] == 14
    assert created[0]["request_fingerprint"] != active_fingerprint
    assert persisted == [created_run_id]
    assert activated == [created_run_id]
