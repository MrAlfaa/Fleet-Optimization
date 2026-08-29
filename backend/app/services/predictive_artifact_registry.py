from __future__ import annotations

import csv
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
import xgboost as xgb

from app.services.ml_model_loader_service import ModelUnavailableError


MODEL_VERSION = "fleetopt-sensor-free-pm-v1"
EXPECTED_ARTIFACT_SHA256 = "26d543f5f2a28ee543b03033bc23c34a18637ae6409251c90abbe9c01d86a17c"
EXPECTED_FEATURE_COUNT = 56
PREDICTIVE_ARTIFACT_ROOT = Path(__file__).resolve().parents[1] / "ml_artifacts" / "predictive_maintenance"
DEFAULT_ARTIFACT_DIR = PREDICTIVE_ARTIFACT_ROOT / MODEL_VERSION

REQUIRED_ARTIFACT_FILES = (
    "global_failure_models.joblib",
    "system_risk_models.joblib",
    "aft_preprocessor.joblib",
    "aft_days_model.json",
    "aft_km_model.json",
    "maintenance_service_rules.csv",
    "feature_schema.json",
    "planning_intervals.json",
    "metrics.json",
    "smoke_test.json",
    "model_card.md",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member_path(destination: Path, member_name: str) -> Path:
    member = Path(member_name)
    if member.is_absolute() or ".." in member.parts:
        raise ValueError(f"Unsafe predictive artifact member: {member_name}")
    target = (destination / member).resolve()
    if destination.resolve() not in target.parents:
        raise ValueError(f"Unsafe predictive artifact member: {member_name}")
    return target


def extract_verified_artifact(source_zip: Path, destination: Path) -> dict[str, Any]:
    source_zip = Path(source_zip)
    destination = Path(destination)
    if not source_zip.is_file():
        raise FileNotFoundError(f"Predictive artifact ZIP is missing: {source_zip}")

    actual_hash = _sha256(source_zip)
    if actual_hash != EXPECTED_ARTIFACT_SHA256:
        raise ValueError("Predictive artifact SHA-256 does not match the approved package")

    with zipfile.ZipFile(source_zip) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        missing = sorted(set(REQUIRED_ARTIFACT_FILES) - set(names))
        unexpected = sorted(set(names) - set(REQUIRED_ARTIFACT_FILES))
        if missing or unexpected:
            raise ValueError(f"Predictive artifact contents are invalid; missing={missing}, unexpected={unexpected}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f".{destination.name}-", dir=destination.parent) as temp_name:
            temporary = Path(temp_name)
            for info in archive.infolist():
                if info.is_dir():
                    continue
                target = _safe_member_path(temporary, info.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)

            schema = json.loads((temporary / "feature_schema.json").read_text(encoding="utf-8"))
            if schema.get("model_version") != MODEL_VERSION:
                raise ValueError("Predictive artifact model version is unsupported")
            if len(schema.get("features") or []) != EXPECTED_FEATURE_COUNT:
                raise ValueError("Predictive artifact feature schema must contain exactly 56 features")

            manifest = {
                "model_version": MODEL_VERSION,
                "source_zip_sha256": actual_hash,
                "feature_schema_version": schema.get("schema_version"),
                "required_files": list(REQUIRED_ARTIFACT_FILES),
                "file_sha256": {name: _sha256(temporary / name) for name in REQUIRED_ARTIFACT_FILES},
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
                raise FileExistsError(f"Refusing to overwrite existing artifact directory: {destination}")
            shutil.copytree(temporary, destination)
    return manifest


@dataclass(frozen=True)
class SensorFreePredictiveArtifacts:
    model_version: str
    feature_schema_version: str
    feature_columns: list[str]
    categorical_features: list[str]
    numeric_features: list[str]
    systems: list[str]
    forbidden_sensor_columns: list[str]
    global_failure_models: dict[str, Any]
    system_risk_models: dict[str, Any]
    aft_preprocessor: Any
    aft_days_model: xgb.Booster
    aft_km_model: xgb.Booster
    service_rules: list[dict[str, Any]]
    planning_intervals: dict[str, Any]
    metrics: dict[str, Any]
    smoke_test: list[dict[str, Any]]
    model_card: str
    thresholds: dict[str, float]


class PredictiveArtifactRegistry:
    def __init__(self, artifact_dir: Path = DEFAULT_ARTIFACT_DIR):
        self.artifact_dir = Path(artifact_dir)
        self._artifacts: SensorFreePredictiveArtifacts | None = None
        self._error: str | None = None
        self._lock = threading.Lock()

    def _json(self, name: str) -> Any:
        return json.loads((self.artifact_dir / name).read_text(encoding="utf-8"))

    def _validate_directory(self) -> None:
        if not self.artifact_dir.is_dir():
            raise FileNotFoundError(f"Predictive artifact directory is missing: {self.artifact_dir}")
        missing = [name for name in REQUIRED_ARTIFACT_FILES if not (self.artifact_dir / name).is_file()]
        if missing:
            raise FileNotFoundError(f"Predictive artifact files are missing: {', '.join(missing)}")
        manifest_path = self.artifact_dir / "artifact_manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError("Predictive artifact manifest is missing")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("source_zip_sha256") != EXPECTED_ARTIFACT_SHA256:
            raise ValueError("Predictive artifact manifest does not match the approved package")
        for name, expected in (manifest.get("file_sha256") or {}).items():
            if name in REQUIRED_ARTIFACT_FILES and _sha256(self.artifact_dir / name) != expected:
                raise ValueError(f"Predictive artifact file hash mismatch: {name}")

    def _load(self) -> SensorFreePredictiveArtifacts:
        self._validate_directory()
        schema = self._json("feature_schema.json")
        metrics = self._json("metrics.json")
        if schema.get("model_version") != MODEL_VERSION:
            raise ValueError(f"Unsupported predictive model version: {schema.get('model_version')}")
        feature_columns = list(schema.get("features") or [])
        if len(feature_columns) != EXPECTED_FEATURE_COUNT:
            raise ValueError("Predictive feature schema must contain exactly 56 features")
        if set(feature_columns) & set(schema.get("forbidden_sensor_columns") or []):
            raise ValueError("Predictive feature schema contains forbidden sensor fields")
        if not metrics.get("quality_gate", {}).get("bundle_pass", False):
            raise ValueError("Predictive artifact quality gate did not pass")

        with (self.artifact_dir / "maintenance_service_rules.csv").open(encoding="utf-8", newline="") as source:
            rules = list(csv.DictReader(source))
        for rule in rules:
            for key in (
                "scheduled_interval_km",
                "scheduled_interval_days",
                "warning_lead_km",
                "warning_lead_days",
                "simulation_failure_life_km",
                "simulation_weibull_shape",
            ):
                rule[key] = float(rule[key])

        days_model = xgb.Booster()
        days_model.load_model(self.artifact_dir / "aft_days_model.json")
        km_model = xgb.Booster()
        km_model.load_model(self.artifact_dir / "aft_km_model.json")
        global_models = joblib.load(self.artifact_dir / "global_failure_models.joblib")
        system_models = joblib.load(self.artifact_dir / "system_risk_models.joblib")
        thresholds = {
            name: float(value["threshold"])
            for name, value in metrics.get("global_failure_models", {}).items()
        }
        return SensorFreePredictiveArtifacts(
            model_version=MODEL_VERSION,
            feature_schema_version=str(schema.get("schema_version")),
            feature_columns=feature_columns,
            categorical_features=list(schema.get("categorical_features") or []),
            numeric_features=list(schema.get("numeric_features") or []),
            systems=list(schema.get("systems") or []),
            forbidden_sensor_columns=list(schema.get("forbidden_sensor_columns") or []),
            global_failure_models=global_models,
            system_risk_models=system_models,
            aft_preprocessor=joblib.load(self.artifact_dir / "aft_preprocessor.joblib"),
            aft_days_model=days_model,
            aft_km_model=km_model,
            service_rules=rules,
            planning_intervals=self._json("planning_intervals.json"),
            metrics=metrics,
            smoke_test=self._json("smoke_test.json"),
            model_card=(self.artifact_dir / "model_card.md").read_text(encoding="utf-8"),
            thresholds=thresholds,
        )

    def get(self) -> SensorFreePredictiveArtifacts:
        if self._artifacts is not None:
            return self._artifacts
        with self._lock:
            if self._artifacts is None:
                try:
                    self._artifacts = self._load()
                    self._error = None
                except Exception as exc:
                    self._error = str(exc)
                    raise ModelUnavailableError(
                        "Sensor-free predictive maintenance artifact is unavailable",
                        {"loaded": False, "error": self._error, "artifact_dir": str(self.artifact_dir)},
                    ) from exc
        return self._artifacts

    def try_load(self) -> SensorFreePredictiveArtifacts | None:
        try:
            return self.get()
        except ModelUnavailableError:
            return None

    def status(self) -> dict[str, Any]:
        artifacts = self.try_load() if self._artifacts is None and self._error is None else self._artifacts
        return {
            "model_version": artifacts.model_version if artifacts else MODEL_VERSION,
            "artifact_dir": str(self.artifact_dir),
            "available": artifacts is not None,
            "loaded": artifacts is not None,
            "degraded": artifacts is None,
            "required_features_count": len(artifacts.feature_columns) if artifacts else EXPECTED_FEATURE_COUNT,
            "feature_schema_version": artifacts.feature_schema_version if artifacts else None,
            "thresholds": artifacts.thresholds if artifacts else {},
            "error": self._error,
        }


predictive_artifact_registry = PredictiveArtifactRegistry()
