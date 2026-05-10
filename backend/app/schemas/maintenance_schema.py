from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.maintenance_model import MAINTENANCE_PRIORITIES, MAINTENANCE_STATUSES, MAINTENANCE_TYPES
from app.utils.validators import validate_choice, validate_non_empty


class MaintenanceRecordCreate(BaseModel):
    vehicle_id: str
    part_id: str | None = None
    part_name: str
    maintenance_type: str
    issue_type: str
    service_date: datetime
    mileage_at_service: float = Field(ge=0)
    technician_name: str | None = None
    service_center: str | None = None
    cost: float | None = Field(default=None, ge=0)
    status: str = "scheduled"
    priority: str = "medium"
    notes: str | None = None

    @field_validator("vehicle_id", "part_name", "maintenance_type", "issue_type")
    @classmethod
    def non_empty(cls, value: str) -> str:
        return validate_non_empty(value)

    @field_validator("maintenance_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        return validate_choice(value, MAINTENANCE_TYPES, "Maintenance type")

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        return validate_choice(value, MAINTENANCE_STATUSES, "Maintenance status")

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, value: str) -> str:
        return validate_choice(value, MAINTENANCE_PRIORITIES, "Priority")


class MaintenanceRecordUpdate(BaseModel):
    part_id: str | None = None
    part_name: str | None = None
    maintenance_type: str | None = None
    issue_type: str | None = None
    service_date: datetime | None = None
    mileage_at_service: float | None = Field(default=None, ge=0)
    technician_name: str | None = None
    service_center: str | None = None
    cost: float | None = Field(default=None, ge=0)
    status: str | None = None
    priority: str | None = None
    notes: str | None = None

    @field_validator("part_name", "maintenance_type", "issue_type")
    @classmethod
    def non_empty_optional(cls, value: str | None) -> str | None:
        return validate_non_empty(value) if value is not None else value

    @field_validator("maintenance_type")
    @classmethod
    def valid_type_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, MAINTENANCE_TYPES, "Maintenance type") if value is not None else value

    @field_validator("status")
    @classmethod
    def valid_status_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, MAINTENANCE_STATUSES, "Maintenance status") if value is not None else value

    @field_validator("priority")
    @classmethod
    def valid_priority_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, MAINTENANCE_PRIORITIES, "Priority") if value is not None else value


class MaintenanceCompleteRequest(BaseModel):
    notes: str | None = None
    cost: float | None = Field(default=None, ge=0)
    technician_name: str | None = None
    service_center: str | None = None


class MaintenanceRecordResponse(BaseModel):
    id: str
    vehicle_id: str
    part_id: str | None = None
    part_name: str
    maintenance_type: str
    issue_type: str
    service_date: datetime
    mileage_at_service: float
    technician_name: str | None = None
    service_center: str | None = None
    cost: float | None = None
    status: str
    priority: str
    notes: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class MaintenanceRecordListResponse(BaseModel):
    items: list[MaintenanceRecordResponse]
    page: int
    limit: int
    total: int
    pages: int
