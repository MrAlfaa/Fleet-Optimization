from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.predictive_model import PREDICTION_INPUT_SOURCES, PREDICTION_RISK_LEVELS
from app.utils.validators import validate_choice, validate_non_empty


class PredictiveRecalculateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trigger: str = "manual_recalculation"
    request_review: bool = False
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("trigger")
    @classmethod
    def valid_trigger(cls, value: str) -> str:
        return validate_choice(value, PREDICTION_INPUT_SOURCES, "Trigger")


class PredictiveMaintenanceRequest(PredictiveRecalculateRequest):
    vehicle_id: str

    @field_validator("vehicle_id")
    @classmethod
    def vehicle_id_required(cls, value: str) -> str:
        return validate_non_empty(value, "vehicle_id")


class BatchPredictiveMaintenanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requests: list[PredictiveMaintenanceRequest] = Field(min_length=1, max_length=100)


class PredictionReviewResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resolution: str
    notes: str = Field(min_length=3, max_length=1000)

    @field_validator("resolution")
    @classmethod
    def valid_resolution(cls, value: str) -> str:
        return validate_choice(value, {"cleared", "confirmed"}, "Resolution")

    @field_validator("notes")
    @classmethod
    def notes_required(cls, value: str) -> str:
        return validate_non_empty(value, "notes")


class PredictiveRiskFilter(BaseModel):
    risk_level: str | None = None

    @field_validator("risk_level")
    @classmethod
    def valid_risk_level(cls, value: str | None) -> str | None:
        return value if value is None else validate_choice(value, PREDICTION_RISK_LEVELS, "Risk level")


class PredictionHistoryResponse(BaseModel):
    vehicle_id: str
    items: list[dict[str, Any]]
