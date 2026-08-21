from datetime import datetime

from pydantic import BaseModel, Field

from app.utils.geo_utils import validate_coordinates


class DriverLocationUpdateRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: float | None = Field(default=None, ge=0)
    heading: float | None = Field(default=None, ge=0, le=360)
    speed_mps: float | None = Field(default=None, ge=0)
    recorded_at: datetime | None = None

    def model_post_init(self, __context) -> None:
        validate_coordinates(self.latitude, self.longitude)
