from datetime import date

from pydantic import BaseModel, Field


class AssignmentValidationRequest(BaseModel):
    vehicle_id: str
    route_id: str


class ReadinessRecommendation(BaseModel):
    type: str
    severity: str
    message: str


class VehicleReadinessResponse(BaseModel):
    vehicle_id: str
    registration_number: str
    vehicle_code: str
    vehicle_type: str
    operational_status: str
    health_status: str
    prediction_risk: str | None = None
    eligible: bool
    readiness_status: str
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FleetReadinessResponse(BaseModel):
    forecast_date: date | None = None
    required_vehicles: int
    eligible_vehicles: int
    warning_vehicles: int
    blocked_vehicles: int
    maintenance_vehicles: int
    capacity_gap: int
    high_demand_zones: list[dict]
    vehicle_readiness: list[VehicleReadinessResponse]
    operational_conflicts: list[ReadinessRecommendation]
    recommendations: list[ReadinessRecommendation]
    data_context: str
    data_context_note: str

