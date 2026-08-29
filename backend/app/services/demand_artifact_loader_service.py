from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.demand_artifact_registry import (
    MODEL_VERSION,
    DemandArtifactError,
    DemandArtifacts,
    demand_artifact_registry,
)


DEMAND_ARTIFACT_DIR = demand_artifact_registry.artifact_dir


class DemandArtifactUnavailableError(Exception):
    def __init__(self, message: str, data: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.data = data or {}


def _artifacts() -> DemandArtifacts:
    try:
        return demand_artifact_registry.get()
    except DemandArtifactError as exc:
        status = demand_artifact_registry.status()
        raise DemandArtifactUnavailableError(
            "Demand forecasting service is temporarily unavailable",
            {"model_version": MODEL_VERSION, "degraded": True, "error": status.get("error")},
        ) from exc


def get_demand_artifact_paths() -> dict[str, str]:
    root = demand_artifact_registry.artifact_dir
    return {
        "artifact_dir": str(root),
        "model_bundle": str(root / "demand_forecasting_model_bundle.joblib"),
        "metrics": str(root / "demand_forecasting_metrics.json"),
        "future_forecast": str(root / "future_demand_forecast.csv"),
        "fleet_recommendations": str(root / "fleet_planning_recommendations.csv"),
        "zone_metadata": str(root / "zone_metadata.csv"),
        "zone_adjacency_graph": str(root / "zone_adjacency_graph.json"),
    }


def load_demand_model_bundle() -> dict[str, Any]:
    artifacts = _artifacts()
    return {
        "final_prophet_models": artifacts.models,
        "adjacency": artifacts.adjacency,
        "configuration": artifacts.configuration,
    }


def load_demand_artifacts() -> DemandArtifacts:
    return _artifacts()


def load_demand_metrics() -> dict[str, Any]:
    return dict(_artifacts().metrics)


def load_future_forecast_csv() -> pd.DataFrame:
    return _artifacts().future_forecast.copy()


def load_fleet_planning_recommendations_csv() -> pd.DataFrame:
    return _artifacts().fleet_recommendations.copy()


def load_zone_metadata_csv() -> pd.DataFrame:
    return _artifacts().zone_metadata.copy()


def load_zone_adjacency_graph() -> dict[str, Any]:
    return dict(_artifacts().adjacency)


def get_demand_artifact_status(load_model: bool = False) -> dict[str, Any]:
    # Registry loading is guarded; an unavailable model degrades this component,
    # not the FastAPI application startup.
    status = demand_artifact_registry.status()
    paths = get_demand_artifact_paths()
    available = bool(status.get("available"))
    artifacts = demand_artifact_registry.try_load() if available else None
    return {
        **status,
        "artifact_path": paths["artifact_dir"],
        "model_bundle_path": paths["model_bundle"],
        "model_bundle_exists": available,
        "missing_files": [] if available else [paths["artifact_dir"]],
        "file_status": {},
        "bundle_keys": ["final_prophet_models", "adjacency", "configuration"] if available else [],
        "forecast_records": len(artifacts.future_forecast) if artifacts else 0,
        "planning_records": len(artifacts.fleet_recommendations) if artifacts else 0,
        "quality_passed": bool((status.get("metrics_snapshot") or {}).get("quality_gate", {}).get("bundle_pass")),
    }
