from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.vehicle_model import (
    FUEL_TYPES,
    VEHICLE_CATEGORIES,
    VEHICLE_HEALTH_STATUSES,
    VEHICLE_ONBOARDING_TYPES,
    VEHICLE_STATUSES,
    VEHICLE_TYPES,
)
from app.utils.validators import validate_choice, validate_non_empty, validate_year


class VehicleLoadProfileInput(BaseModel):
    profile_code: str
    capacity_m3: float = Field(gt=0)
    cargo_length_cm: float = Field(gt=0)
    cargo_width_cm: float = Field(gt=0)
    cargo_height_cm: float = Field(gt=0)
    max_parcels: int = Field(gt=0)
    max_stack_layers: int = Field(default=1, gt=0)
    vehicle_max_stack_weight_kg: float = Field(gt=0)
    is_refrigerated: bool = False
    temp_min_celsius: float | None = None
    temp_max_celsius: float | None = None
    is_hazmat_certified: bool = False
    has_tail_lift: bool = False
    available_from: str = "00:00"
    available_until: str = "23:59"

    @field_validator("profile_code")
    @classmethod
    def normalize_profile_code(cls, value: str) -> str:
        return validate_non_empty(value).upper()

    @field_validator("available_from", "available_until")
    @classmethod
    def valid_hhmm(cls, value: str) -> str:
        try:
            hour, minute = (int(part) for part in value.split(":"))
        except (TypeError, ValueError):
            raise ValueError("Availability time must use HH:MM") from None
        if len(value) != 5 or not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError("Availability time must use HH:MM")
        return value

    @model_validator(mode="after")
    def validate_capabilities(self):
        if self.available_until <= self.available_from:
            raise ValueError("available_until must be after available_from")
        if self.is_refrigerated:
            if self.temp_min_celsius is None or self.temp_max_celsius is None:
                raise ValueError("A complete temperature range is required for refrigerated vehicles")
            if self.temp_min_celsius >= self.temp_max_celsius:
                raise ValueError("The refrigeration temperature range is invalid")
        return self


class VehicleCreate(BaseModel):
    vehicle_code: str
    registration_number: str
    vehicle_type: str
    vehicle_category: str | None = None
    brand: str
    model: str
    year: int
    fuel_type: str = "electric"
    current_mileage: float = Field(default=0, ge=0)
    in_service_date: datetime | None = None
    payload_capacity_kg: float | None = Field(default=None, gt=0)
    load_profile: VehicleLoadProfileInput | None = None
    onboarding_type: str = "existing_fleet"
    battery_capacity_kwh: float | None = Field(default=None, ge=0)
    image_url: str | None = None
    assigned_driver_id: str | None = None
    status: str = "inactive"
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

    @field_validator("vehicle_category")
    @classmethod
    def valid_vehicle_category(cls, value: str | None) -> str | None:
        return validate_choice(value, VEHICLE_CATEGORIES, "Vehicle category") if value is not None else value

    @field_validator("fuel_type")
    @classmethod
    def valid_fuel_type(cls, value: str) -> str:
        return validate_choice(value, FUEL_TYPES, "Fuel type")

    @field_validator("onboarding_type")
    @classmethod
    def valid_onboarding_type(cls, value: str) -> str:
        return validate_choice(value, VEHICLE_ONBOARDING_TYPES, "Vehicle onboarding type")

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
    vehicle_category: str | None = None
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    fuel_type: str | None = None
    current_mileage: float | None = Field(default=None, ge=0)
    in_service_date: datetime | None = None
    payload_capacity_kg: float | None = Field(default=None, gt=0)
    load_profile: VehicleLoadProfileInput | None = None
    onboarding_type: str | None = None
    battery_capacity_kwh: float | None = Field(default=None, ge=0)
    image_url: str | None = None
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

    @field_validator("vehicle_category")
    @classmethod
    def valid_vehicle_category_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, VEHICLE_CATEGORIES, "Vehicle category") if value is not None else value

    @field_validator("fuel_type")
    @classmethod
    def valid_fuel_type_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, FUEL_TYPES, "Fuel type") if value is not None else value

    @field_validator("onboarding_type")
    @classmethod
    def valid_onboarding_type_optional(cls, value: str | None) -> str | None:
        return validate_choice(value, VEHICLE_ONBOARDING_TYPES, "Vehicle onboarding type") if value is not None else value

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
    vehicle_category: str | None = None
    brand: str
    model: str
    year: int
    fuel_type: str
    current_mileage: float
    in_service_date: datetime | None = None
    payload_capacity_kg: float | None = None
    load_profile: dict | None = None
    onboarding_type: str = "existing_fleet"
    commissioning_status: str = "not_started"
    battery_capacity_kwh: float | None = None
    image_url: str | None = None
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


class VehicleLifecycleRequest(BaseModel):
    reason: str | None = None
