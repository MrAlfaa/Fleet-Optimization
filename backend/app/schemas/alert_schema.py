from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.alert_model import ALERT_SEVERITIES, ALERT_STATUSES, ALERT_TYPES
from app.utils.validators import validate_choice, validate_non_empty


class AlertCreate(BaseModel):
    alert_type: str
    severity: str
    title: str
    message: str
    linked_vehicle_id: str | None = None
    linked_part_id: str | None = None
    linked_maintenance_record_id: str | None = None
    status: str = "active"
    created_by_system: bool = False

    @field_validator("alert_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        return validate_choice(value, ALERT_TYPES, "Alert type")

    @field_validator("severity")
    @classmethod
    def valid_severity(cls, value: str) -> str:
        return validate_choice(value, ALERT_SEVERITIES, "Alert severity")

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        return validate_choice(value, ALERT_STATUSES, "Alert status")

    @field_validator("title", "message")
    @classmethod
    def non_empty(cls, value: str) -> str:
        return validate_non_empty(value)


class AlertUpdate(BaseModel):
    alert_type: str | None = None
    severity: str | None = None
    title: str | None = None
    message: str | None = None
    status: str | None = None

    @field_validator("alert_type")
    @classmethod
    def valid_type_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, ALERT_TYPES, "Alert type") if value is not None else value

    @field_validator("severity")
    @classmethod
    def valid_severity_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, ALERT_SEVERITIES, "Alert severity") if value is not None else value

    @field_validator("status")
    @classmethod
    def valid_status_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, ALERT_STATUSES, "Alert status") if value is not None else value


class AlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    title: str
    message: str
    linked_vehicle_id: str | None = None
    linked_part_id: str | None = None
    linked_maintenance_record_id: str | None = None
    status: str
    created_by_system: bool
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    page: int
    limit: int
    total: int
    pages: int
