import json
from pathlib import Path
from typing import Any

import joblib


PREDICTIVE_ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "ml_artifacts" / "predictive_maintenance"
PREDICTIVE_MODEL_PATH = PREDICTIVE_ARTIFACT_DIR / "ev_predictive_maintenance_model_bundle.joblib"
PREDICTIVE_FEATURES_PATH = PREDICTIVE_ARTIFACT_DIR / "ev_predictive_maintenance_features.json"
PREDICTIVE_METRICS_PATH = PREDICTIVE_ARTIFACT_DIR / "ev_predictive_maintenance_metrics.json"

_predictive_maintenance_bundle: dict[str, Any] | None = None
_predictive_maintenance_error: str | None = None


class ModelUnavailableError(Exception):
    def __init__(self, message: str, data: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.data = data or {}


def validate_artifact_exists(path: Path) -> None:
    if not path.exists():
        raise ModelUnavailableError(
            "Predictive maintenance model artifact is unavailable",
            {"expected_path": str(path), "loaded": False},
        )


def load_joblib_model(path: Path) -> Any:
    validate_artifact_exists(path)
    try:
        return joblib.load(path)
    except Exception as exc:
        raise ModelUnavailableError(
            "Predictive maintenance model artifact could not be loaded",
            {"expected_path": str(path), "loaded": False, "error": str(exc)},
        ) from exc


def _read_json_file(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def get_feature_columns_from_file() -> list[str]:
    data = _read_json_file(PREDICTIVE_FEATURES_PATH, [])
    return data if isinstance(data, list) else []


def get_metrics_from_file() -> dict[str, Any]:
    data = _read_json_file(PREDICTIVE_METRICS_PATH, {})
    return data if isinstance(data, dict) else {}


def get_predictive_maintenance_bundle() -> dict[str, Any]:
    global _predictive_maintenance_bundle, _predictive_maintenance_error

    if _predictive_maintenance_bundle is not None:
        return _predictive_maintenance_bundle

    loaded = load_joblib_model(PREDICTIVE_MODEL_PATH)
    if not isinstance(loaded, dict):
        _predictive_maintenance_error = "Model bundle is not a dictionary"
        raise ModelUnavailableError(
            "Predictive maintenance model bundle has an unsupported format",
            {"expected_path": str(PREDICTIVE_MODEL_PATH), "loaded": False, "error": _predictive_maintenance_error},
        )

    loaded.setdefault("feature_columns", get_feature_columns_from_file())
    loaded.setdefault("metrics", get_metrics_from_file())
    _predictive_maintenance_bundle = loaded
    _predictive_maintenance_error = None
    return loaded


def get_artifact_metadata(load: bool = False) -> dict[str, Any]:
    bundle_keys: list[str] = []
    feature_columns = get_feature_columns_from_file()
    metrics = get_metrics_from_file()
    loaded = _predictive_maintenance_bundle is not None
    error = _predictive_maintenance_error

    if load:
        try:
            bundle = get_predictive_maintenance_bundle()
            bundle_keys = sorted(bundle.keys())
            feature_columns = bundle.get("feature_columns") or feature_columns
            metrics = bundle.get("metrics") or metrics
            loaded = True
            error = None
        except ModelUnavailableError as exc:
            error = exc.data.get("error") or exc.message

    return {
        "artifact_path": str(PREDICTIVE_MODEL_PATH),
        "artifact_exists": PREDICTIVE_MODEL_PATH.exists(),
        "loaded": loaded,
        "available": PREDICTIVE_MODEL_PATH.exists() and (error is None),
        "bundle_keys": bundle_keys,
        "required_features_count": len(feature_columns),
        "required_features": feature_columns,
        "metrics_snapshot": metrics,
        "error": error,
    }
