from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from app.services.demand_artifact_registry import (
    EXPECTED_ARTIFACT_SHA256,
    DEFAULT_ARTIFACT_DIR,
    MODEL_VERSION,
    REQUIRED_RUNTIME_FILES,
    DemandArtifactRegistry,
)


def test_committed_demand_artifact_matches_approved_manifest_and_file_hashes() -> None:
    manifest = json.loads((DEFAULT_ARTIFACT_DIR / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert manifest["model_version"] == MODEL_VERSION
    assert manifest["source_zip_sha256"] == EXPECTED_ARTIFACT_SHA256
    assert manifest["dataset_start"] == "2021-04-02"
    assert manifest["dataset_end"] == "2026-04-01"
    assert manifest["forecast_start"] == "2026-04-02"
    assert manifest["forecast_end"] == "2026-05-01"
    assert set(REQUIRED_RUNTIME_FILES).issubset(path.name for path in DEFAULT_ARTIFACT_DIR.iterdir())
    for name, expected_hash in manifest["file_sha256"].items():
        assert hashlib.sha256((DEFAULT_ARTIFACT_DIR / name).read_bytes()).hexdigest() == expected_hash


def test_registry_loads_approved_colombo_models_and_runtime_policy(tmp_path: Path) -> None:
    destination = tmp_path / MODEL_VERSION
    shutil.copytree(DEFAULT_ARTIFACT_DIR, destination)

    artifacts = DemandArtifactRegistry(destination).get()

    assert artifacts.model_version == MODEL_VERSION
    assert artifacts.training_data_version == "fleetopt-sim-v1"
    assert artifacts.feature_schema_version == "2.0"
    assert artifacts.validation_scope == "synthetic_research_mvp"
    assert len(artifacts.models) == 15
    assert set(artifacts.models) == set(artifacts.zone_metadata["zone_id"])
    assert artifacts.spatial_alpha == pytest.approx(0.15)
    assert artifacts.orders_per_vehicle == 12
    assert artifacts.demand_thresholds == (12.0, 18.0, 25.0)
    assert artifacts.metrics["quality_gate"]["bundle_pass"] is True
    assert artifacts.metrics["dataset"]["start"] == "2021-04-02"
    assert artifacts.metrics["dataset"]["end"] == "2026-04-01"
    forecast_dates = artifacts.future_forecast["ds"]
    assert forecast_dates.min() == "2026-04-02"
    assert forecast_dates.max() == "2026-05-01"
    assert len(artifacts.future_forecast) == 450


def test_registry_reports_degraded_state_when_artifact_is_missing(tmp_path: Path) -> None:
    registry = DemandArtifactRegistry(tmp_path / "missing")

    assert registry.try_load() is None
    status = registry.status()

    assert status["available"] is False
    assert status["degraded"] is True
    assert status["model_version"] == MODEL_VERSION
    assert "missing" in status["error"].lower()
