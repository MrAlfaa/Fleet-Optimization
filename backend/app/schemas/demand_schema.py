from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.models.demand_model import DEMAND_LEVELS, DEMAND_REFRESH_SOURCES
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


class FleetPlanningRecommendationListResponse(BaseModel):
    items: list[dict[str, Any]]
    page: int
    limit: int
    total: int
    pages: int


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


class DemandModelMetricsResponse(BaseModel):
    baseline_prophet: dict[str, Any] | None = None
    graph_enhanced_prophet: dict[str, Any] | None = None
    configuration: dict[str, Any] | None = None


class DemandForecastRefreshRequest(BaseModel):
    days: int | None = Field(default=30, ge=1, le=365)
    save_to_database: bool = True
    source: Literal["artifact", "model"] = "artifact"

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        return validate_choice(value, DEMAND_REFRESH_SOURCES, "Refresh source")


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
