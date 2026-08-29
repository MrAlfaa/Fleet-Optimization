from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.delivery_model import DELIVERY_PRIORITIES, DELIVERY_STATUSES
from app.utils.geo_utils import validate_coordinates
from app.utils.validators import validate_choice, validate_non_empty


class ParcelLoadProfileInput(BaseModel):
    length_cm: float = Field(gt=0)
    width_cm: float = Field(gt=0)
    height_cm: float = Field(gt=0)
    volume_m3: float | None = Field(default=None, gt=0)
    fragile: bool = False
    stackable: bool = True
    max_stack_weight_kg: float = Field(default=0, ge=0)
    loading_orientation_fixed: bool = False
    hazardous: bool = False
    hazmat_class: str | None = Field(default=None, max_length=32)
    requires_refrigeration: bool = False
    temp_min_celsius: float | None = None
    temp_max_celsius: float | None = None
    two_person_lift: bool = False
    do_not_tilt: bool = False
    service_type: Literal["door_to_door", "collection_point", "locker_drop", "standard"] = "door_to_door"

    @model_validator(mode="after")
    def validate_handling_profile(self):
        calculated = (self.length_cm * self.width_cm * self.height_cm) / 1_000_000
        if self.volume_m3 is not None and abs(self.volume_m3 - calculated) / calculated > 0.10:
            raise ValueError("volume_m3 must match parcel dimensions within 10 percent")
        self.volume_m3 = round(calculated, 8)
        if self.hazardous and not (self.hazmat_class or "").strip():
            raise ValueError("hazmat_class is required for a hazardous parcel")
        if self.requires_refrigeration:
            if self.temp_min_celsius is None or self.temp_max_celsius is None:
                raise ValueError("A complete temperature range is required for refrigerated parcels")
            if self.temp_min_celsius >= self.temp_max_celsius:
                raise ValueError("The refrigeration temperature range is invalid")
        return self


class DeliveryOrderCreate(BaseModel):
    order_code: str | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    pickup_latitude: float | None = None
    pickup_longitude: float | None = None
    drop_latitude: float
    drop_longitude: float
    pickup_address: str | None = None
    drop_address: str | None = None
    zone_id: str | None = None
    zone_assignment_method: str | None = None
    is_demo: bool = False
    parcel_weight: float | None = Field(default=None, ge=0)
    parcel_volume: float | None = Field(default=None, ge=0)
    load_profile: ParcelLoadProfileInput | None = None
    priority: str = "medium"
    delivery_status: str = "pending"
    assigned_vehicle_id: str | None = None
    assigned_driver_id: str | None = None
    delivery_date: date
    delivery_period: Literal["first_half", "second_half"]
    scheduled_date: datetime | None = None

    @field_validator("order_code", "customer_name", "customer_phone", "pickup_address", "drop_address", "zone_id")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return validate_non_empty(value) if value is not None else value

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, value: str) -> str:
        return validate_choice(value, DELIVERY_PRIORITIES, "Delivery priority")

    @field_validator("delivery_status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        return validate_choice(value, DELIVERY_STATUSES, "Delivery status")

    def model_post_init(self, __context) -> None:
        if self.pickup_latitude is not None and self.pickup_longitude is not None:
            validate_coordinates(self.pickup_latitude, self.pickup_longitude)
        validate_coordinates(self.drop_latitude, self.drop_longitude)
        if self.load_profile is not None:
            if self.parcel_weight is None or self.parcel_weight <= 0:
                raise ValueError("parcel_weight is required when a load profile is provided")
            self.parcel_volume = self.load_profile.volume_m3


class DeliveryOrderUpdate(BaseModel):
    order_code: str | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    pickup_latitude: float | None = None
    pickup_longitude: float | None = None
    drop_latitude: float | None = None
    drop_longitude: float | None = None
    pickup_address: str | None = None
    drop_address: str | None = None
    zone_id: str | None = None
    zone_assignment_method: str | None = None
    is_demo: bool | None = None
    parcel_weight: float | None = Field(default=None, ge=0)
    parcel_volume: float | None = Field(default=None, ge=0)
    load_profile: ParcelLoadProfileInput | None = None
    priority: str | None = None
    delivery_status: str | None = None
    assigned_vehicle_id: str | None = None
    assigned_driver_id: str | None = None
    scheduled_date: datetime | None = None
    delivery_date: date | None = None
    delivery_period: Literal["first_half", "second_half"] | None = None

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, value: str | None) -> str | None:
        return validate_choice(value, DELIVERY_PRIORITIES, "Delivery priority") if value is not None else value

    @field_validator("delivery_status")
    @classmethod
    def valid_status(cls, value: str | None) -> str | None:
        return validate_choice(value, DELIVERY_STATUSES, "Delivery status") if value is not None else value


class DeliveryAssignRequest(BaseModel):
    vehicle_id: str
    driver_id: str | None = None


class DeliveryStatusUpdateRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        return validate_choice(value, DELIVERY_STATUSES, "Delivery status")


class DeliveryCancelRequest(BaseModel):
    reason: str | None = None


class BulkDeliveryOrderCreate(BaseModel):
    orders: list[DeliveryOrderCreate] = Field(min_length=1, max_length=100)


class DeliveryOrderResponse(BaseModel):
    id: str
    order_code: str
    customer_name: str | None = None
    customer_phone: str | None = None
    pickup_latitude: float
    pickup_longitude: float
    drop_latitude: float
    drop_longitude: float
    pickup_address: str | None = None
    drop_address: str | None = None
    zone_id: str | None = None
    operational_zone_id: str | None = None
    source_zone_id: str | None = None
    zone_assignment_method: str | None = None
    zone_distance_km: float | None = None
    within_service_area: bool = True
    is_demo: bool = False
    parcel_weight: float | None = None
    parcel_volume: float | None = None
    load_profile: dict | None = None
    load_planning_status: str = "unplanned"
    active_consolidation_id: str | None = None
    active_load_plan_id: str | None = None
    priority: str
    delivery_status: str
    assigned_vehicle_id: str | None = None
    assigned_driver_id: str | None = None
    scheduled_date: datetime | None = None
    delivery_date: str | None = None
    delivery_period: str | None = None
    delivery_window_start: datetime | None = None
    delivery_window_end: datetime | None = None
    pickup_source: str | None = None
    created_at: datetime
    updated_at: datetime


class DeliveryOrderListResponse(BaseModel):
    items: list[DeliveryOrderResponse]
    page: int
    limit: int
    total: int
    pages: int
