from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.vehicle_part_model import PART_STATUSES, RISK_LEVELS
from app.utils.validators import validate_choice, validate_non_empty


class VehiclePartCreate(BaseModel):
    part_name: str
    part_category: str
    risk_level: str = "unknown"
    risk_score: float = Field(default=0, ge=0, le=100)
    last_serviced_date: datetime | None = None
    next_predicted_maintenance_date: datetime | None = None
    status: str = "unknown"
    notes: str | None = None

    @field_validator("part_name", "part_category")
    @classmethod
    def non_empty(cls, value: str) -> str:
        return validate_non_empty(value)

    @field_validator("risk_level")
    @classmethod
    def valid_risk_level(cls, value: str) -> str:
        return validate_choice(value, RISK_LEVELS, "Risk level")

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        return validate_choice(value, PART_STATUSES, "Part status")


class VehiclePartUpdate(BaseModel):
    part_name: str | None = None
    part_category: str | None = None
    risk_level: str | None = None
    risk_score: float | None = Field(default=None, ge=0, le=100)
    last_serviced_date: datetime | None = None
    next_predicted_maintenance_date: datetime | None = None
    status: str | None = None
    notes: str | None = None

    @field_validator("part_name", "part_category")
    @classmethod
    def non_empty_optional(cls, value: str | None) -> str | None:
        return validate_non_empty(value) if value is not None else value

    @field_validator("risk_level")
    @classmethod
    def valid_risk_level_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, RISK_LEVELS, "Risk level") if value is not None else value

    @field_validator("status")
    @classmethod
    def valid_status_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, PART_STATUSES, "Part status") if value is not None else value


class VehiclePartResponse(BaseModel):
    id: str
    vehicle_id: str
    part_name: str
    part_category: str
    risk_level: str
    risk_score: float
    last_serviced_date: datetime | None = None
    next_predicted_maintenance_date: datetime | None = None
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    archived_at: datetime | None = None
    archived_by: str | None = None


class VehiclePartLifecycleRequest(BaseModel):
    reason: str | None = None
