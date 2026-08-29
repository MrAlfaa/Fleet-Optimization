from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator

from app.models.demand_model import DEMAND_LEVELS
from app.utils.validators import validate_choice, validate_non_empty


class DemandZoneResponse(BaseModel):
    id: str | None = None
    zone_id: str
    zone_name: str | None = None
    city: str | None = None
    state: str | None = None
    zone_lat: float | None = None
    zone_lng: float | None = None
    customer_count: int | None = None
    is_active: bool = True


class DemandForecastResponse(BaseModel):
    id: str | None = None
    zone_id: str
    forecast_date: datetime
    baseline_prophet_forecast: float | None = None
    graph_enhanced_forecast: float
    predicted_demand: float
    forecast_horizon_days: int | None = None
    model_type: str
    model_run_id: str | None = None


class DemandForecastListResponse(BaseModel):
    items: list[dict[str, Any]]
    page: int
    limit: int
    total: int
    pages: int
    active_run: dict[str, Any] | None = None


class ZoneForecastResponse(BaseModel):
    zone_id: str
    days: int
    items: list[dict[str, Any]]


class FleetPlanningRecommendationResponse(BaseModel):
    id: str | None = None
    zone_id: str
    forecast_date: datetime
    predicted_demand: float
    demand_level: str
    estimated_required_vehicles: int
    recommended_action: str
    model_run_id: str | None = None
    model_version: str | None = None


class FleetPlanningRecommendationListResponse(BaseModel):
    items: list[dict[str, Any]]
    page: int
    limit: int
    total: int
    pages: int
    active_run: dict[str, Any] | None = None


class DemandModelStatusResponse(BaseModel):
    artifact_path: str
    model_bundle_path: str
    model_bundle_exists: bool
    loaded: bool
    available: bool
    missing_files: list[str]
    file_status: dict[str, Any]
    bundle_keys: list[str]
    zones_count: int
    forecast_records: int
    planning_records: int
    metrics_snapshot: dict[str, Any]
    error: str | None = None
    model_version: str | None = None
    quality_passed: bool = False
    degraded: bool = False
    operational_state: str | None = None
    active_run: dict[str, Any] | None = None


class DemandComparisonItemResponse(BaseModel):
    date: datetime
    operational_zone_id: str
    zone_display_name: str
    predicted_demand: float
    local_actual_demand: int | None = None
    variance_orders: float | None = None
    variance_percentage: float | None = None
    baseline_forecast: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    demand_level: str
    estimated_required_vehicles: int
    recommended_action: str
    model_version: str | None = None
    generated_at: datetime | None = None
    final_predicted_demand: float | None = None


class DemandModelMetricsResponse(BaseModel):
    baseline_prophet: dict[str, Any] | None = None
    graph_enhanced_prophet: dict[str, Any] | None = None
    configuration: dict[str, Any] | None = None


class DemandForecastRefreshRequest(BaseModel):
    days: Literal[7, 14, 30] = 30
    save_to_database: Literal[True] = True
    source: Literal["model"] = "model"


class DemandRunMetadataResponse(BaseModel):
    model_run_id: str
    run_type: str | None = None
    model_version: str | None = None
    status: str | None = None
    horizon_days: int
    source_requested: str | None = None
    effective_source: str | None = None
    fallback_used: bool = False
    request_fingerprint: str | None = None
    forecast_start_date: str | None = None
    forecast_end_date: str | None = None
    zones_count: int
    records_generated: int
    generated_at: str | None = None
    activated_at: str | None = None
    failed_at: str | None = None
    planning_window: dict[str, Any]


class DemandRunHistoryResponse(BaseModel):
    items: list[DemandRunMetadataResponse]
    limit: int


class DemandForecastSummaryResponse(BaseModel):
    total_zones: int
    forecast_records: int
    high_demand_zones: int
    very_high_demand_zones: int
    total_predicted_demand_next_7_days: float
    total_required_vehicles_next_7_days: int
    top_demand_zones: list[dict[str, Any]]
    latest_forecast_date: str | None = None


class DemandDashboardResponse(DemandForecastSummaryResponse):
    pass


class DemandFilter(BaseModel):
    zone_id: str | None = None
    demand_level: str | None = None

    @field_validator("zone_id")
    @classmethod
    def clean_zone_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_non_empty(value, "zone_id")

    @field_validator("demand_level")
    @classmethod
    def valid_demand_level(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_choice(value, DEMAND_LEVELS, "Demand level")
