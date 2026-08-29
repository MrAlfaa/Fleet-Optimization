import json
import hashlib
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib


ROUTE_MODEL_VERSION = "fleetopt-route-synthetic-v1"
ROUTE_ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "ml_artifacts" / "route_prediction" / ROUTE_MODEL_VERSION
ROUTE_MODEL_FILE = "route_prediction_model_bundle.joblib"
ROUTE_METRICS_FILE = "route_prediction_metrics.json"
ROUTE_SCHEMA_FILE = "route_prediction_schema.json"
ROUTE_SAMPLE_INPUT_FILE = "route_prediction_sample_input.json"
ROUTE_MANIFEST_FILE = "artifact_manifest.json"


class RouteArtifactUnavailableError(Exception):
    def __init__(self, message: str, data: dict[str, Any]):
        self.message = message
        self.data = data
        super().__init__(message)


def get_route_artifact_paths() -> dict[str, str]:
    return {
        "artifact_dir": str(ROUTE_ARTIFACT_DIR),
        "model_bundle": str(ROUTE_ARTIFACT_DIR / ROUTE_MODEL_FILE),
        "metrics": str(ROUTE_ARTIFACT_DIR / ROUTE_METRICS_FILE),
        "schema": str(ROUTE_ARTIFACT_DIR / ROUTE_SCHEMA_FILE),
        "sample_input": str(ROUTE_ARTIFACT_DIR / ROUTE_SAMPLE_INPUT_FILE),
    }


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_artifact_files() -> dict[str, Any]:
    manifest = _load_json(ROUTE_ARTIFACT_DIR / ROUTE_MANIFEST_FILE) or {}
    expected_files = manifest.get("files") or {}
    mismatches = []
    for filename, expected_hash in expected_files.items():
        path = ROUTE_ARTIFACT_DIR / filename
        if not path.exists() or _sha256(path).lower() != str(expected_hash).lower():
            mismatches.append(filename)
    return {
        "manifest": manifest,
        "verified": bool(expected_files) and not mismatches,
        "hash_mismatches": mismatches,
    }


def _install_sklearn_pickle_compatibility() -> None:
    try:
        import sklearn.compose._column_transformer as column_transformer
    except Exception:
        return

    if not hasattr(column_transformer, "_RemainderColsList"):
        class _RemainderColsList(list):
            pass

        column_transformer._RemainderColsList = _RemainderColsList


def _patch_loaded_sklearn_objects(value: Any, seen: set[int] | None = None) -> None:
    if seen is None:
        seen = set()
    object_id = id(value)
    if object_id in seen:
        return
    seen.add(object_id)

    if value.__class__.__name__ == "SimpleImputer" and not hasattr(value, "_fill_dtype"):
        value._fill_dtype = getattr(value, "_fit_dtype", object)

    if isinstance(value, dict):
        for item in value.values():
            _patch_loaded_sklearn_objects(item, seen)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _patch_loaded_sklearn_objects(item, seen)
        return
    if hasattr(value, "steps"):
        for _, step in value.steps:
            _patch_loaded_sklearn_objects(step, seen)
    if hasattr(value, "transformers"):
        for _, transformer, _ in value.transformers:
            _patch_loaded_sklearn_objects(transformer, seen)
    if hasattr(value, "transformers_"):
        for _, transformer, _ in value.transformers_:
            _patch_loaded_sklearn_objects(transformer, seen)
    if hasattr(value, "__dict__"):
        for item in value.__dict__.values():
            if isinstance(item, (dict, list, tuple)) or hasattr(item, "__dict__"):
                _patch_loaded_sklearn_objects(item, seen)


@lru_cache(maxsize=1)
def load_route_model_bundle() -> dict[str, Any]:
    model_path = ROUTE_ARTIFACT_DIR / ROUTE_MODEL_FILE
    if not model_path.exists():
        raise RouteArtifactUnavailableError(
            "Route prediction model artifact is unavailable",
            {"missing_files": [ROUTE_MODEL_FILE], "artifact_path": str(ROUTE_ARTIFACT_DIR)},
        )
    verification = _verify_artifact_files()
    if not verification["verified"]:
        raise RouteArtifactUnavailableError(
            "Route prediction artifact integrity verification failed",
            {"hash_mismatches": verification["hash_mismatches"], "artifact_path": str(ROUTE_ARTIFACT_DIR)},
        )
    try:
        _install_sklearn_pickle_compatibility()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
            bundle = joblib.load(model_path)
        _patch_loaded_sklearn_objects(bundle)
    except Exception as exc:  # noqa: BLE001 - return a clean API-facing error.
        raise RouteArtifactUnavailableError(
            "Route prediction model artifact could not be loaded",
            {"error": str(exc), "artifact_path": str(model_path)},
        ) from exc
    if not isinstance(bundle, dict):
        raise RouteArtifactUnavailableError(
            "Route prediction model artifact has an invalid format",
            {"artifact_path": str(model_path)},
        )
    return bundle


def load_route_metrics() -> dict[str, Any] | None:
    return _load_json(ROUTE_ARTIFACT_DIR / ROUTE_METRICS_FILE)


def load_route_schema() -> dict[str, Any] | None:
    return _load_json(ROUTE_ARTIFACT_DIR / ROUTE_SCHEMA_FILE)


def load_route_sample_input() -> dict[str, Any] | None:
    return _load_json(ROUTE_ARTIFACT_DIR / ROUTE_SAMPLE_INPUT_FILE)


def get_route_artifact_status(load_model: bool = False) -> dict[str, Any]:
    paths = get_route_artifact_paths()
    missing_files = [
        filename
        for filename in [ROUTE_MODEL_FILE, ROUTE_METRICS_FILE, ROUTE_SCHEMA_FILE]
        if not (ROUTE_ARTIFACT_DIR / filename).exists()
    ]
    optional_missing = []
    if not (ROUTE_ARTIFACT_DIR / ROUTE_SAMPLE_INPUT_FILE).exists():
        optional_missing.append(ROUTE_SAMPLE_INPUT_FILE)

    schema = load_route_schema() or {}
    metrics = load_route_metrics()
    verification = _verify_artifact_files()
    quality_gate = (metrics or {}).get("quality_gate") or {}
    quality_gate_passed = quality_gate.get("bundle_pass") is True
    loaded = False
    model_keys: list[str] = []
    load_error = None
    if load_model and ROUTE_MODEL_FILE not in missing_files:
        try:
            bundle = load_route_model_bundle()
            loaded = True
            model_keys = sorted(bundle.keys())
        except RouteArtifactUnavailableError as exc:
            load_error = exc.data

    feature_columns = schema.get("feature_columns") or []
    return {
        "artifact_path": paths["artifact_dir"],
        "model_file_exists": ROUTE_MODEL_FILE not in missing_files,
        "loaded": loaded,
        "available": not missing_files and load_error is None and verification["verified"] and quality_gate_passed,
        "model_version": ROUTE_MODEL_VERSION,
        "integrity_verified": verification["verified"],
        "hash_mismatches": verification["hash_mismatches"],
        "quality_gate_passed": quality_gate_passed,
        "model_keys": model_keys,
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
        "metrics": metrics,
        "missing_files": missing_files,
        "optional_missing_files": optional_missing,
        "load_error": load_error,
        "paths": paths,
    }
