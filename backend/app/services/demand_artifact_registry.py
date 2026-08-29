from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


MODEL_VERSION = "fleetopt-demand-synthetic-v1"
EXPECTED_ARTIFACT_SHA256 = "df8bcdcf82c56aa9683a12accabc8f47d3792490867806b280135e46c071140b"
DEMAND_ARTIFACT_ROOT = Path(__file__).resolve().parents[1] / "ml_artifacts" / "demand_forecasting"
DEFAULT_ARTIFACT_DIR = DEMAND_ARTIFACT_ROOT / MODEL_VERSION
DEMAND_THRESHOLDS = (12.0, 18.0, 25.0)
ORDERS_PER_VEHICLE = 12

REQUIRED_RUNTIME_FILES = (
    "demand_forecasting_model_bundle.joblib",
    "demand_forecasting_metrics.json",
    "future_demand_forecast.csv",
    "fleet_planning_recommendations.csv",
    "zone_metadata.csv",
    "zone_adjacency_graph.json",
)


class DemandArtifactError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member_path(destination: Path, member_name: str) -> Path:
    member = Path(member_name)
    if member.is_absolute() or ".." in member.parts:
        raise ValueError(f"Unsafe demand artifact member: {member_name}")
    target = (destination / member).resolve()
    if destination.resolve() not in target.parents:
        raise ValueError(f"Unsafe demand artifact member: {member_name}")
    return target


def _validated_forecast_window(metrics: dict[str, Any], forecast: pd.DataFrame) -> dict[str, str]:
    dataset = metrics.get("dataset") or {}
    dataset_start = pd.to_datetime(dataset.get("start"), errors="coerce")
    dataset_end = pd.to_datetime(dataset.get("end"), errors="coerce")
    forecast_dates = pd.to_datetime(forecast.get("ds"), errors="coerce")
    zone_ids = forecast.get("zone_id", pd.Series(dtype=str)).astype(str)

    if pd.isna(dataset_start) or pd.isna(dataset_end) or dataset_start > dataset_end:
        raise ValueError("Demand artifact dataset date range is invalid")
    if forecast_dates.isna().any() or forecast_dates.empty:
        raise ValueError("Demand artifact forecast dates are invalid")
    if len(forecast) != 450 or zone_ids.nunique() != 15 or forecast_dates.dt.date.nunique() != 30:
        raise ValueError("Demand artifact forecast must contain 30 days for exactly 15 zones")

    expected_start = dataset_end.normalize() + pd.Timedelta(days=1)
    expected_dates = pd.date_range(expected_start, periods=30, freq="D")
    actual_dates = pd.DatetimeIndex(sorted(forecast_dates.dt.normalize().unique()))
    if not actual_dates.equals(expected_dates):
        raise ValueError("Demand artifact forecast must start the day after the training dataset ends")
    counts_by_date = forecast_dates.dt.normalize().value_counts()
    if not counts_by_date.eq(15).all():
        raise ValueError("Demand artifact forecast must contain all 15 zones on every forecast date")

    return {
        "dataset_start": dataset_start.date().isoformat(),
        "dataset_end": dataset_end.date().isoformat(),
        "forecast_start": expected_dates.min().date().isoformat(),
        "forecast_end": expected_dates.max().date().isoformat(),
    }


def extract_verified_demand_artifact(source_zip: Path, destination: Path) -> dict[str, Any]:
    source_zip = Path(source_zip)
    destination = Path(destination)
    if not source_zip.is_file():
        raise FileNotFoundError(f"Demand artifact ZIP is missing: {source_zip}")

    actual_hash = _sha256(source_zip)
    if actual_hash != EXPECTED_ARTIFACT_SHA256:
        raise ValueError("Demand artifact SHA-256 does not match the approved package")

    with zipfile.ZipFile(source_zip) as archive:
        archive_files = {info.filename for info in archive.infolist() if not info.is_dir()}
        missing = sorted(set(REQUIRED_RUNTIME_FILES) - archive_files)
        if missing:
            raise ValueError(f"Demand artifact runtime files are missing: {missing}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f".{MODEL_VERSION}-", dir=destination.parent) as temp_name:
            temporary = Path(temp_name)
            for name in REQUIRED_RUNTIME_FILES:
                target = _safe_member_path(temporary, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)

            metrics = json.loads((temporary / "demand_forecasting_metrics.json").read_text(encoding="utf-8"))
            metadata = metrics.get("metadata") or {}
            if metadata.get("model_version") != MODEL_VERSION:
                raise ValueError("Demand artifact model version is unsupported")
            if not metrics.get("quality_gate", {}).get("bundle_pass", False):
                raise ValueError("Demand artifact quality gate did not pass")

            forecast_window = _validated_forecast_window(
                metrics,
                pd.read_csv(temporary / "future_demand_forecast.csv"),
            )

            zones = pd.read_csv(temporary / "zone_metadata.csv")
            zone_ids = zones.get("zone_id", pd.Series(dtype=str)).astype(str).tolist()
            if len(zone_ids) != 15 or len(set(zone_ids)) != 15 or any(not value.startswith("LK_") for value in zone_ids):
                raise ValueError("Demand artifact must contain exactly 15 unique LK operational zones")

            manifest = {
                "model_version": MODEL_VERSION,
                "source_zip_sha256": actual_hash,
                "training_data_version": metadata.get("training_data_version"),
                "feature_schema_version": metadata.get("feature_schema_version"),
                **forecast_window,
                "required_runtime_files": list(REQUIRED_RUNTIME_FILES),
                "file_sha256": {name: _sha256(temporary / name) for name in REQUIRED_RUNTIME_FILES},
            }
            (temporary / "artifact_manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
            )

            if destination.exists():
                existing_manifest = destination / "artifact_manifest.json"
                if existing_manifest.is_file():
                    existing = json.loads(existing_manifest.read_text(encoding="utf-8"))
                    if existing.get("source_zip_sha256") == actual_hash:
                        return existing
                raise FileExistsError(f"Refusing to overwrite existing demand artifact: {destination}")
            shutil.copytree(temporary, destination)
    return manifest


@dataclass(frozen=True)
class DemandArtifacts:
    model_version: str
    training_data_version: str
    feature_schema_version: str
    validation_scope: str
    models: dict[str, Any]
    adjacency: dict[str, list[dict[str, Any]]]
    zone_metadata: pd.DataFrame
    future_forecast: pd.DataFrame
    fleet_recommendations: pd.DataFrame
    metrics: dict[str, Any]
    configuration: dict[str, Any]
    spatial_alpha: float
    demand_thresholds: tuple[float, float, float]
    orders_per_vehicle: int


class DemandArtifactRegistry:
    def __init__(self, artifact_dir: Path = DEFAULT_ARTIFACT_DIR):
        self.artifact_dir = Path(artifact_dir)
        self._artifacts: DemandArtifacts | None = None
        self._error: str | None = None
        self._lock = threading.Lock()

    def _validate_directory(self) -> dict[str, Any]:
        if not self.artifact_dir.is_dir():
            raise FileNotFoundError(f"Demand artifact directory is missing: {self.artifact_dir}")
        missing = [name for name in REQUIRED_RUNTIME_FILES if not (self.artifact_dir / name).is_file()]
        if missing:
            raise FileNotFoundError(f"Demand artifact files are missing: {', '.join(missing)}")
        manifest_path = self.artifact_dir / "artifact_manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError("Demand artifact manifest is missing")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("source_zip_sha256") != EXPECTED_ARTIFACT_SHA256:
            raise ValueError("Demand artifact manifest does not match the approved package")
        for name, expected_hash in (manifest.get("file_sha256") or {}).items():
            if name in REQUIRED_RUNTIME_FILES and _sha256(self.artifact_dir / name) != expected_hash:
                raise ValueError(f"Demand artifact file hash mismatch: {name}")
        return manifest

    def _load(self) -> DemandArtifacts:
        self._validate_directory()
        metrics = json.loads((self.artifact_dir / "demand_forecasting_metrics.json").read_text(encoding="utf-8"))
        metadata = metrics.get("metadata") or {}
        if metadata.get("model_version") != MODEL_VERSION:
            raise ValueError(f"Unsupported demand model version: {metadata.get('model_version')}")
        if not metrics.get("quality_gate", {}).get("bundle_pass", False):
            raise ValueError("Demand artifact quality gate did not pass")

        bundle = joblib.load(self.artifact_dir / "demand_forecasting_model_bundle.joblib")
        models = bundle.get("final_prophet_models") if isinstance(bundle, dict) else None
        if not isinstance(models, dict) or len(models) != 15:
            raise ValueError("Demand artifact must contain 15 final Prophet models")
        zone_metadata = pd.read_csv(self.artifact_dir / "zone_metadata.csv")
        zone_ids = set(zone_metadata["zone_id"].astype(str))
        if set(models) != zone_ids:
            raise ValueError("Demand model zones do not match packaged zone metadata")
        if any(not zone.startswith("LK_") for zone in zone_ids):
            raise ValueError("Demand model exposes unsupported non-operational zone IDs")

        future_forecast = pd.read_csv(self.artifact_dir / "future_demand_forecast.csv")
        _validated_forecast_window(metrics, future_forecast)
        configuration = dict(bundle.get("configuration") or {})
        return DemandArtifacts(
            model_version=MODEL_VERSION,
            training_data_version=str(metadata.get("training_data_version") or "unknown"),
            feature_schema_version=str(metadata.get("feature_schema_version") or "unknown"),
            validation_scope=str(metadata.get("validation_scope") or "unknown"),
            models=models,
            adjacency=dict(bundle.get("adjacency") or {}),
            zone_metadata=zone_metadata,
            future_forecast=future_forecast,
            fleet_recommendations=pd.read_csv(self.artifact_dir / "fleet_planning_recommendations.csv"),
            metrics=metrics,
            configuration=configuration,
            spatial_alpha=float(configuration.get("alpha_spatial_influence", 0.15)),
            demand_thresholds=DEMAND_THRESHOLDS,
            orders_per_vehicle=ORDERS_PER_VEHICLE,
        )

    def get(self) -> DemandArtifacts:
        if self._artifacts is not None:
            return self._artifacts
        with self._lock:
            if self._artifacts is None:
                try:
                    self._artifacts = self._load()
                    self._error = None
                except Exception as exc:
                    self._error = str(exc)
                    raise DemandArtifactError("Demand forecasting artifact is unavailable") from exc
        return self._artifacts

    def try_load(self) -> DemandArtifacts | None:
        try:
            return self.get()
        except DemandArtifactError:
            return None

    def status(self) -> dict[str, Any]:
        artifacts = self.try_load() if self._artifacts is None and self._error is None else self._artifacts
        return {
            "model_version": artifacts.model_version if artifacts else MODEL_VERSION,
            "training_data_version": artifacts.training_data_version if artifacts else None,
            "feature_schema_version": artifacts.feature_schema_version if artifacts else None,
            "validation_scope": artifacts.validation_scope if artifacts else None,
            "artifact_dir": str(self.artifact_dir),
            "available": artifacts is not None,
            "loaded": artifacts is not None,
            "degraded": artifacts is None,
            "zones_count": len(artifacts.models) if artifacts else 0,
            "spatial_alpha": artifacts.spatial_alpha if artifacts else None,
            "demand_thresholds": list(artifacts.demand_thresholds) if artifacts else list(DEMAND_THRESHOLDS),
            "orders_per_vehicle": artifacts.orders_per_vehicle if artifacts else ORDERS_PER_VEHICLE,
            "metrics_snapshot": artifacts.metrics if artifacts else {},
            "error": self._error,
        }


demand_artifact_registry = DemandArtifactRegistry()
