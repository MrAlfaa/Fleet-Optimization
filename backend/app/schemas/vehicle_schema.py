from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.vehicle_model import FUEL_TYPES, VEHICLE_HEALTH_STATUSES, VEHICLE_STATUSES, VEHICLE_TYPES
from app.utils.validators import validate_choice, validate_non_empty, validate_year


class VehicleCreate(BaseModel):
    vehicle_code: str
    registration_number: str
    vehicle_type: str
    brand: str
    model: str
    year: int
    fuel_type: str = "electric"
    current_mileage: float = Field(default=0, ge=0)
    battery_capacity_kwh: float | None = Field(default=None, ge=0)
    assigned_driver_id: str | None = None
    status: str = "active"
    health_status: str = "unknown"
    last_service_date: datetime | None = None
    next_service_due_date: datetime | None = None

    @field_validator("vehicle_code", "registration_number", "brand", "model")
    @classmethod
    def non_empty(cls, value: str) -> str:
        return validate_non_empty(value)

    @field_validator("year")
    @classmethod
    def valid_year(cls, value: int) -> int:
        return validate_year(value)

    @field_validator("vehicle_type")
    @classmethod
    def valid_vehicle_type(cls, value: str) -> str:
        return validate_choice(value, VEHICLE_TYPES, "Vehicle type")

    @field_validator("fuel_type")
    @classmethod
    def valid_fuel_type(cls, value: str) -> str:
        return validate_choice(value, FUEL_TYPES, "Fuel type")

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        return validate_choice(value, VEHICLE_STATUSES, "Vehicle status")

    @field_validator("health_status")
    @classmethod
    def valid_health_status(cls, value: str) -> str:
        return validate_choice(value, VEHICLE_HEALTH_STATUSES, "Health status")


class VehicleUpdate(BaseModel):
    vehicle_code: str | None = None
    registration_number: str | None = None
    vehicle_type: str | None = None
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    fuel_type: str | None = None
    current_mileage: float | None = Field(default=None, ge=0)
    battery_capacity_kwh: float | None = Field(default=None, ge=0)
    assigned_driver_id: str | None = None
    status: str | None = None
    health_status: str | None = None
    last_service_date: datetime | None = None
    next_service_due_date: datetime | None = None

    @field_validator("vehicle_code", "registration_number", "brand", "model")
    @classmethod
    def non_empty_optional(cls, value: str | None) -> str | None:
        return validate_non_empty(value) if value is not None else value

    @field_validator("year")
    @classmethod
    def valid_year_optional(cls, value: int | None) -> int | None:
        return validate_year(value) if value is not None else value

    @field_validator("vehicle_type")
    @classmethod
    def valid_vehicle_type_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, VEHICLE_TYPES, "Vehicle type") if value is not None else value

    @field_validator("fuel_type")
    @classmethod
    def valid_fuel_type_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, FUEL_TYPES, "Fuel type") if value is not None else value

    @field_validator("status")
    @classmethod
    def valid_status_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, VEHICLE_STATUSES, "Vehicle status") if value is not None else value

    @field_validator("health_status")
    @classmethod
    def valid_health_status_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, VEHICLE_HEALTH_STATUSES, "Health status") if value is not None else value


class VehicleResponse(BaseModel):
    id: str
    vehicle_code: str
    registration_number: str
    vehicle_type: str
    brand: str
    model: str
    year: int
    fuel_type: str
    current_mileage: float
    battery_capacity_kwh: float | None = None
    assigned_driver_id: str | None = None
    status: str
    health_status: str
    last_service_date: datetime | None = None
    next_service_due_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class VehicleListResponse(BaseModel):
    items: list[VehicleResponse]
    page: int
    limit: int
    total: int
    pages: int
