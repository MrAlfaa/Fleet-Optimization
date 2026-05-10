from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.predictive_model import PREDICTION_INPUT_SOURCES, PREDICTION_RISK_LEVELS
from app.utils.validators import validate_choice, validate_non_empty


class EVSensorInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    SoC: float | None = None
    SoH: float | None = None
    Battery_Voltage: float | None = None
    Battery_Current: float | None = None
    Battery_Temperature: float | None = None
    Charge_Cycles: float | None = None
    Motor_Temperature: float | None = None
    Motor_Vibration: float | None = None
    Motor_Torque: float | None = None
    Motor_RPM: float | None = None
    Brake_Pad_Wear: float | None = None
    Brake_Pressure: float | None = None
    Tire_Pressure: float | None = None
    Suspension_Load: float | None = None
    Driving_Speed: float | None = None
    Distance_Traveled: float | None = None
    Route_Roughness: float | None = None
    Ambient_Temperature: float | None = None


class PredictiveMaintenanceRequest(BaseModel):
    vehicle_id: str
    part_id: str | None = None
    input_source: str
    sensor_data: EVSensorInput

    @field_validator("vehicle_id")
    @classmethod
    def vehicle_id_required(cls, value: str) -> str:
        return validate_non_empty(value, "vehicle_id")

    @field_validator("input_source")
    @classmethod
    def valid_input_source(cls, value: str) -> str:
        return validate_choice(value, PREDICTION_INPUT_SOURCES, "Input source")


class PredictiveMaintenanceResponse(BaseModel):
    vehicle_id: str
    failure_prediction: int
    failure_probability: float
    risk_level: str
    maintenance_type_id: int | None = None
    maintenance_type_name: str | None = None
    predicted_rul: float | None = None
    rul_unit: str | None = None
    next_maintenance_date: datetime | None = None
    recommended_action: str
    alert_created: bool
    prediction_id: str


class BatchPredictiveMaintenanceRequest(BaseModel):
    requests: list[PredictiveMaintenanceRequest] = Field(min_length=1, max_length=100)


class PredictionHistoryResponse(BaseModel):
    vehicle_id: str
    items: list[dict[str, Any]]


class PredictionListResponse(BaseModel):
    items: list[dict[str, Any]]
    page: int
    limit: int
    total: int
    pages: int


class ModelStatusResponse(BaseModel):
    artifact_path: str
    artifact_exists: bool
    loaded: bool
    available: bool
    bundle_keys: list[str]
    required_features_count: int
    required_features: list[str]
    metrics_snapshot: dict[str, Any]
    error: str | None = None


class ManualEVSensorInputTemplate(BaseModel):
    input_source: str = "manual"
    sensor_data: dict[str, float | int]


class PredictiveRiskFilter(BaseModel):
    risk_level: str | None = None

    @field_validator("risk_level")
    @classmethod
    def valid_risk_level(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_choice(value, PREDICTION_RISK_LEVELS, "Risk level")
