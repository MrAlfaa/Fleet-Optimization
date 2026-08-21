from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.delivery_model import DELIVERY_PRIORITIES
from app.models.route_model import ROUTE_STATUSES
from app.utils.geo_utils import validate_coordinates
from app.utils.validators import validate_choice, validate_non_empty


class RouteSegmentPredictionRequest(BaseModel):
    pickup_latitude: float
    pickup_longitude: float
    drop_latitude: float
    drop_longitude: float
    weather: str | None = None
    traffic: str | None = None
    vehicle_type: str | None = None
    area: str | None = None
    category: str | None = None
    agent_age: float | None = Field(default=None, ge=0)
    agent_rating: float | None = Field(default=None, ge=0)
    order_date: str | None = None
    order_time: str | None = None

    model_config = ConfigDict(extra="allow")

    def model_post_init(self, __context) -> None:
        validate_coordinates(self.pickup_latitude, self.pickup_longitude)
        validate_coordinates(self.drop_latitude, self.drop_longitude)


class RouteSegmentPredictionResponse(BaseModel):
    distance_km: float
    predicted_eta_minutes: float
    delay_probability: float
    delay_prediction: int
    delay_risk_level: str
    route_cost_score: float


class BatchRouteSegmentPredictionRequest(BaseModel):
    segments: list[RouteSegmentPredictionRequest] = Field(min_length=1, max_length=100)


class DeliveryStopInput(BaseModel):
    order_code: str | None = None
    drop_latitude: float
    drop_longitude: float
    pickup_latitude: float | None = None
    pickup_longitude: float | None = None
    zone_id: str | None = None
    priority: str | None = "medium"
    parcel_weight: float | None = Field(default=None, ge=0)

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, value: str | None) -> str | None:
        return validate_choice(value, DELIVERY_PRIORITIES, "Delivery priority") if value is not None else value

    def model_post_init(self, __context) -> None:
        validate_coordinates(self.drop_latitude, self.drop_longitude)
        if self.pickup_latitude is not None and self.pickup_longitude is not None:
            validate_coordinates(self.pickup_latitude, self.pickup_longitude)


class RouteOptimizationRequest(BaseModel):
    depot_latitude: float
    depot_longitude: float
    depot_name: str | None = None
    route_name: str | None = None
    vehicle_id: str | None = None
    driver_id: str | None = None
    delivery_order_ids: list[str] | None = None
    delivery_stops: list[DeliveryStopInput] | None = None
    use_ml_cost: bool = True
    include_demand_context: bool = True
    include_maintenance_context: bool = True
    include_weather_context: bool = True
    save_route: bool = True

    @field_validator("depot_name", "route_name")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return validate_non_empty(value) if value is not None else value

    def model_post_init(self, __context) -> None:
        validate_coordinates(self.depot_latitude, self.depot_longitude)
        if not self.delivery_order_ids and not self.delivery_stops:
            raise ValueError("Provide delivery_order_ids or delivery_stops")


class RouteDispatchRequest(BaseModel):
    vehicle_id: str | None = None
    driver_id: str | None = None
    notes: str | None = None


class RoutePlanResponse(BaseModel):
    id: str
    route_code: str
    route_name: str | None = None
    vehicle_id: str | None = None
    driver_id: str | None = None
    depot_latitude: float
    depot_longitude: float
    depot_name: str | None = None
    delivery_order_ids: list[str]
    optimized_stop_order: list[dict[str, Any]]
    total_predicted_eta_minutes: float
    total_route_cost_score: float
    average_delay_probability: float
    optimization_method: str
    status: str
    demand_context: dict[str, Any] | None = None
    maintenance_context: dict[str, Any] | None = None
    weather_context: dict[str, Any] | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
    dispatched_at: datetime | None = None
    completed_at: datetime | None = None


class RoutePlanListResponse(BaseModel):
    items: list[RoutePlanResponse]
    page: int
    limit: int
    total: int
    pages: int


class RouteModelStatusResponse(BaseModel):
    artifact_path: str
    model_file_exists: bool
    loaded: bool
    available: bool
    feature_count: int
    metrics: dict[str, Any] | None = None
    missing_files: list[str] = []


class RouteDashboardSummaryResponse(BaseModel):
    total_route_plans: int
    optimized_routes_count: int
    dispatched_routes_count: int
    active_routes_count: int
    average_route_delay_probability: float
    total_predicted_eta_today: float
    pending_deliveries: int
    delivered_orders_today: int
