from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class LoadOptimizationJobCreate(BaseModel):
    delivery_date: date
    delivery_period: Literal["first_half", "second_half"]
    order_ids: list[str] | None = Field(default=None, max_length=1000)
    seed: int = Field(default=17, ge=0, le=2_147_483_647)
    consolidation_id: str | None = Field(default=None, pattern=r"^PCID\d{8}(1H|2H)\d{3}$")


class ParcelConsolidationCreate(BaseModel):
    delivery_date: date
    delivery_period: Literal["first_half", "second_half"]
    seed: int = Field(default=17, ge=0, le=2_147_483_647)


class PhysicalVehicleAssignment(BaseModel):
    vehicle_id: str


class LoadPlanApproval(BaseModel):
    option_id: str | None = None
