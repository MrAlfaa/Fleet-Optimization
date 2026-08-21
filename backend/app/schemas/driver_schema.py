from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.alert_model import ALERT_SEVERITIES
from app.utils.route_utils import DELIVERY_STATUSES
from app.utils.validators import validate_choice, validate_non_empty


class DriverDeliveryStatusUpdateRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        return validate_choice(value, DELIVERY_STATUSES, "Delivery status")


class DriverIssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=1000)
    vehicle_id: str | None = None
    route_id: str | None = None
    severity: str = "warning"
    category: str = "other"
    stop_id: str | None = None

    @field_validator("title", "message")
    @classmethod
    def non_empty(cls, value: str) -> str:
        return validate_non_empty(value)

    @field_validator("severity")
    @classmethod
    def valid_severity(cls, value: str) -> str:
        return validate_choice(value, ALERT_SEVERITIES, "Alert severity")

    @field_validator("category")
    @classmethod
    def valid_category(cls, value: str) -> str:
        return validate_choice(value, {"battery", "brakes", "tires", "motor_drivetrain", "charging", "suspension", "thermal_system", "other"}, "Issue category")


class DeliveryIncompleteRequest(BaseModel):
    reason: str
    details: str | None = Field(default=None, max_length=1000)
    idempotency_key: str = Field(min_length=16, max_length=200)

    @model_validator(mode="after")
    def validate_reason(self):
        allowed = {"customer_unavailable", "incorrect_address", "access_restricted", "parcel_damaged", "vehicle_issue", "weather_or_route_issue", "other"}
        if self.reason not in allowed:
            raise ValueError("Invalid incomplete delivery reason")
        if self.reason == "other" and not (self.details or "").strip():
            raise ValueError("Details are required when reason is other")
        return self


TIRE_CONDITIONS = {"normal", "worn", "damaged"}
BRAKE_CONDITIONS = {"normal", "noisy", "reduced_response", "warning_light"}
CHARGING_CONDITIONS = {"normal", "intermittent", "not_charging", "port_damaged"}
VEHICLE_DAMAGE_LEVELS = {"none", "minor", "major"}
DASHBOARD_WARNING_LEVELS = {"none", "amber", "red"}
OBSERVATION_LEVELS = {"none", "mild", "severe"}
CONDITION_CHANGE_LEVELS = {"none", "minor", "significant"}
CHARGING_PROBLEM_LEVELS = {"none", "intermittent", "failed"}


class PreTripInspectionRequest(BaseModel):
    odometer: float = Field(ge=0, le=5_000_000)
    battery_soc: float = Field(ge=0, le=100)
    tire_condition: str
    brake_condition: str
    charging_condition: str
    vehicle_damage: str
    dashboard_warning: str
    unusual_noise: str
    unusual_vibration: str
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("tire_condition")
    @classmethod
    def valid_tire_condition(cls, value: str) -> str:
        return validate_choice(value, TIRE_CONDITIONS, "Tire condition")

    @field_validator("brake_condition")
    @classmethod
    def valid_brake_condition(cls, value: str) -> str:
        return validate_choice(value, BRAKE_CONDITIONS, "Brake condition")

    @field_validator("charging_condition")
    @classmethod
    def valid_charging_condition(cls, value: str) -> str:
        return validate_choice(value, CHARGING_CONDITIONS, "Charging condition")

    @field_validator("vehicle_damage")
    @classmethod
    def valid_vehicle_damage(cls, value: str) -> str:
        return validate_choice(value, VEHICLE_DAMAGE_LEVELS, "Vehicle damage")

    @field_validator("dashboard_warning")
    @classmethod
    def valid_dashboard_warning(cls, value: str) -> str:
        return validate_choice(value, DASHBOARD_WARNING_LEVELS, "Dashboard warning")

    @field_validator("unusual_noise", "unusual_vibration")
    @classmethod
    def valid_observation(cls, value: str) -> str:
        return validate_choice(value, OBSERVATION_LEVELS, "Observation")


class PostTripInspectionRequest(BaseModel):
    ending_odometer: float = Field(ge=0, le=5_000_000)
    ending_battery_soc: float = Field(ge=0, le=100)
    tire_condition_change: str
    brake_condition_change: str
    charging_problem: str
    vehicle_damage: str
    dashboard_warning: str
    unusual_noise: str
    unusual_vibration: str
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("tire_condition_change", "brake_condition_change")
    @classmethod
    def valid_condition_change(cls, value: str) -> str:
        return validate_choice(value, CONDITION_CHANGE_LEVELS, "Condition change")

    @field_validator("charging_problem")
    @classmethod
    def valid_charging_problem(cls, value: str) -> str:
        return validate_choice(value, CHARGING_PROBLEM_LEVELS, "Charging problem")

    @field_validator("vehicle_damage")
    @classmethod
    def valid_vehicle_damage(cls, value: str) -> str:
        return validate_choice(value, VEHICLE_DAMAGE_LEVELS, "Vehicle damage")

    @field_validator("dashboard_warning")
    @classmethod
    def valid_dashboard_warning(cls, value: str) -> str:
        return validate_choice(value, DASHBOARD_WARNING_LEVELS, "Dashboard warning")

    @field_validator("unusual_noise", "unusual_vibration")
    @classmethod
    def valid_observation(cls, value: str) -> str:
        return validate_choice(value, OBSERVATION_LEVELS, "Observation")

    def validate_against_starting_odometer(self, starting_odometer: float) -> None:
        if self.ending_odometer < starting_odometer:
            raise ValueError("Ending odometer cannot be lower than the starting odometer")
