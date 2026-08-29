from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from app.services.predictive_artifact_registry import (
    EXPECTED_ARTIFACT_SHA256,
    DEFAULT_ARTIFACT_DIR,
    REQUIRED_ARTIFACT_FILES,
    PredictiveArtifactRegistry,
)


def test_committed_artifact_matches_approved_manifest_and_file_hashes() -> None:
    manifest = json.loads((DEFAULT_ARTIFACT_DIR / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_zip_sha256"] == EXPECTED_ARTIFACT_SHA256
    assert manifest["model_version"] == "fleetopt-sensor-free-pm-v1"
    assert set(REQUIRED_ARTIFACT_FILES).issubset(path.name for path in DEFAULT_ARTIFACT_DIR.iterdir())
    for name, expected_hash in manifest["file_sha256"].items():
        assert hashlib.sha256((DEFAULT_ARTIFACT_DIR / name).read_bytes()).hexdigest() == expected_hash


def test_registry_loads_schema_thresholds_rules_and_models_from_verified_directory(tmp_path: Path) -> None:
    destination = tmp_path / "fleetopt-sensor-free-pm-v1"
    shutil.copytree(DEFAULT_ARTIFACT_DIR, destination)
    registry = PredictiveArtifactRegistry(destination)

    artifacts = registry.get()
    status = registry.status()

    assert artifacts.model_version == "fleetopt-sensor-free-pm-v1"
    assert len(artifacts.feature_columns) == 56
    assert artifacts.thresholds["failure_30_days"] == pytest.approx(0.12448132780082988)
    assert artifacts.thresholds["failure_2000_km"] == pytest.approx(0.07312925170068027)
    assert len(artifacts.service_rules) == 37
    assert set(artifacts.global_failure_models["models"]) == {"failure_30_days", "failure_2000_km"}
    assert len(artifacts.system_risk_models["models"]) == 14
    assert status["available"] is True
    assert status["degraded"] is False


def test_registry_reports_degraded_status_without_crashing_when_artifact_is_missing(tmp_path: Path) -> None:
    registry = PredictiveArtifactRegistry(tmp_path / "missing")

    assert registry.try_load() is None
    status = registry.status()

    assert status["available"] is False
    assert status["degraded"] is True
    assert "missing" in status["error"].lower()
