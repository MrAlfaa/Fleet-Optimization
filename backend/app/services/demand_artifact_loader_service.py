import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


DEMAND_ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "ml_artifacts" / "demand_forecasting"
DEMAND_MODEL_PATH = DEMAND_ARTIFACT_DIR / "demand_forecasting_model_bundle.joblib"
DEMAND_METRICS_PATH = DEMAND_ARTIFACT_DIR / "demand_forecasting_metrics.json"
FUTURE_FORECAST_PATH = DEMAND_ARTIFACT_DIR / "future_demand_forecast.csv"
FLEET_RECOMMENDATIONS_PATH = DEMAND_ARTIFACT_DIR / "fleet_planning_recommendations.csv"
ZONE_METADATA_PATH = DEMAND_ARTIFACT_DIR / "zone_metadata.csv"
ZONE_ADJACENCY_PATH = DEMAND_ARTIFACT_DIR / "zone_adjacency_graph.json"
ZONE_TRAINING_DATA_PATH = DEMAND_ARTIFACT_DIR / "zone_daily_demand_training_data.csv"

_demand_model_bundle: dict[str, Any] | None = None
_demand_model_error: str | None = None


class DemandArtifactUnavailableError(Exception):
    def __init__(self, message: str, data: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.data = data or {}


def get_demand_artifact_paths() -> dict[str, str]:
    return {
        "artifact_dir": str(DEMAND_ARTIFACT_DIR),
        "model_bundle": str(DEMAND_MODEL_PATH),
        "metrics": str(DEMAND_METRICS_PATH),
        "future_forecast": str(FUTURE_FORECAST_PATH),
        "fleet_recommendations": str(FLEET_RECOMMENDATIONS_PATH),
        "zone_metadata": str(ZONE_METADATA_PATH),
        "zone_adjacency_graph": str(ZONE_ADJACENCY_PATH),
        "training_data": str(ZONE_TRAINING_DATA_PATH),
    }


def _file_status() -> dict[str, dict[str, Any]]:
    paths = {
        "model_bundle": DEMAND_MODEL_PATH,
        "metrics": DEMAND_METRICS_PATH,
        "future_forecast": FUTURE_FORECAST_PATH,
        "fleet_recommendations": FLEET_RECOMMENDATIONS_PATH,
        "zone_metadata": ZONE_METADATA_PATH,
        "zone_adjacency_graph": ZONE_ADJACENCY_PATH,
        "training_data": ZONE_TRAINING_DATA_PATH,
    }
    return {
        key: {"path": str(path), "exists": path.exists(), "size_bytes": path.stat().st_size if path.exists() else 0}
        for key, path in paths.items()
    }


def _required_missing_files() -> list[str]:
    required = [FUTURE_FORECAST_PATH, FLEET_RECOMMENDATIONS_PATH, ZONE_METADATA_PATH]
    return [str(path) for path in required if not path.exists()]


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise DemandArtifactUnavailableError(
            "Demand forecasting artifact is unavailable",
            {"missing_files": [str(path)], "artifact_path": str(DEMAND_ARTIFACT_DIR)},
        )
    try:
        return pd.read_csv(path)
    except Exception as exc:
        raise DemandArtifactUnavailableError(
            "Demand forecasting artifact could not be read",
            {"file": str(path), "error": str(exc), "artifact_path": str(DEMAND_ARTIFACT_DIR)},
        ) from exc


def load_demand_model_bundle() -> dict[str, Any]:
    global _demand_model_bundle, _demand_model_error

    if _demand_model_bundle is not None:
        return _demand_model_bundle
    if not DEMAND_MODEL_PATH.exists():
        _demand_model_error = "Model bundle file is missing"
        raise DemandArtifactUnavailableError(
            "Demand forecasting model bundle is unavailable",
            {"missing_files": [str(DEMAND_MODEL_PATH)], "artifact_path": str(DEMAND_ARTIFACT_DIR)},
        )

    try:
        loaded = joblib.load(DEMAND_MODEL_PATH)
        if not isinstance(loaded, dict):
            raise TypeError("Demand model bundle is not a dictionary")
        _demand_model_bundle = loaded
        _demand_model_error = None
        return loaded
    except Exception as exc:
        _demand_model_error = str(exc)
        raise DemandArtifactUnavailableError(
            "Demand forecasting model bundle could not be loaded",
            {"file": str(DEMAND_MODEL_PATH), "error": str(exc), "artifact_path": str(DEMAND_ARTIFACT_DIR)},
        ) from exc


def load_demand_metrics() -> dict[str, Any]:
    data = _read_json(DEMAND_METRICS_PATH, {})
    return data if isinstance(data, dict) else {}


def load_future_forecast_csv() -> pd.DataFrame:
    return _read_csv(FUTURE_FORECAST_PATH)


def load_fleet_planning_recommendations_csv() -> pd.DataFrame:
    return _read_csv(FLEET_RECOMMENDATIONS_PATH)


def load_zone_metadata_csv() -> pd.DataFrame:
    return _read_csv(ZONE_METADATA_PATH)


def load_zone_adjacency_graph() -> dict[str, Any]:
    data = _read_json(ZONE_ADJACENCY_PATH, {})
    return data if isinstance(data, dict) else {}


def get_demand_artifact_status(load_model: bool = False) -> dict[str, Any]:
    bundle_keys: list[str] = []
    zones_count = 0
    forecast_records = 0
    planning_records = 0
    loaded = _demand_model_bundle is not None
    error = _demand_model_error

    if ZONE_METADATA_PATH.exists():
        try:
            zones_count = len(pd.read_csv(ZONE_METADATA_PATH, usecols=["zone_id"]))
        except Exception:
            zones_count = 0
    if FUTURE_FORECAST_PATH.exists():
        try:
            forecast_records = len(pd.read_csv(FUTURE_FORECAST_PATH, usecols=["zone_id"]))
        except Exception:
            forecast_records = 0
    if FLEET_RECOMMENDATIONS_PATH.exists():
        try:
            planning_records = len(pd.read_csv(FLEET_RECOMMENDATIONS_PATH, usecols=["zone_id"]))
        except Exception:
            planning_records = 0

    if load_model:
        try:
            bundle = load_demand_model_bundle()
            bundle_keys = sorted(bundle.keys())
            loaded = True
            error = None
        except DemandArtifactUnavailableError as exc:
            error = exc.data.get("error") or exc.message

    missing_required = _required_missing_files()
    return {
        "artifact_path": str(DEMAND_ARTIFACT_DIR),
        "model_bundle_path": str(DEMAND_MODEL_PATH),
        "model_bundle_exists": DEMAND_MODEL_PATH.exists(),
        "loaded": loaded,
        "available": not missing_required,
        "missing_files": missing_required,
        "file_status": _file_status(),
        "bundle_keys": bundle_keys,
        "zones_count": zones_count,
        "forecast_records": forecast_records,
        "planning_records": planning_records,
        "metrics_snapshot": load_demand_metrics(),
        "error": error,
    }
