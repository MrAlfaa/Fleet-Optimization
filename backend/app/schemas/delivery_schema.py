from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.delivery_model import DELIVERY_PRIORITIES, DELIVERY_STATUSES
from app.utils.geo_utils import validate_coordinates
from app.utils.validators import validate_choice, validate_non_empty


class DeliveryOrderCreate(BaseModel):
    order_code: str | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    pickup_latitude: float
    pickup_longitude: float
    drop_latitude: float
    drop_longitude: float
    pickup_address: str | None = None
    drop_address: str | None = None
    zone_id: str | None = None
    zone_assignment_method: str | None = None
    is_demo: bool = False
    parcel_weight: float | None = Field(default=None, ge=0)
    parcel_volume: float | None = Field(default=None, ge=0)
    priority: str = "medium"
    delivery_status: str = "pending"
    assigned_vehicle_id: str | None = None
    assigned_driver_id: str | None = None
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
        validate_coordinates(self.pickup_latitude, self.pickup_longitude)
        validate_coordinates(self.drop_latitude, self.drop_longitude)


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
    priority: str | None = None
    delivery_status: str | None = None
    assigned_vehicle_id: str | None = None
    assigned_driver_id: str | None = None
    scheduled_date: datetime | None = None

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
    priority: str
    delivery_status: str
    assigned_vehicle_id: str | None = None
    assigned_driver_id: str | None = None
    scheduled_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DeliveryOrderListResponse(BaseModel):
    items: list[DeliveryOrderResponse]
    page: int
    limit: int
    total: int
    pages: int
