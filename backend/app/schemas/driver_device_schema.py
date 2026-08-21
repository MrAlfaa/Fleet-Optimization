from pydantic import BaseModel, Field, field_validator

from app.utils.validators import validate_email_address, validate_password_strength


class DriverAdminCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    email: str
    phone: str | None = Field(default=None, max_length=30)
    temporary_password: str
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def email_value(cls, value: str) -> str:
        return validate_email_address(value)

    @field_validator("temporary_password")
    @classmethod
    def password_value(cls, value: str) -> str:
        return validate_password_strength(value)


class DriverAdminUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    username: str | None = Field(default=None, min_length=3, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    email: str | None = None
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("email")
    @classmethod
    def email_value(cls, value: str | None) -> str | None:
        return validate_email_address(value) if value is not None else None


class DriverDeviceResetRequest(BaseModel):
    temporary_password: str

    @field_validator("temporary_password")
    @classmethod
    def password_value(cls, value: str) -> str:
        return validate_password_strength(value)


class DriverDeviceEnrollRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    temporary_password: str = Field(min_length=1)
    installation_id: str = Field(min_length=16, max_length=200)
    device_name: str = Field(min_length=1, max_length=120)
    device_model: str = Field(min_length=1, max_length=120)
    android_version: str = Field(min_length=1, max_length=50)
    app_version: str = Field(min_length=1, max_length=50)


class DriverDeviceSessionRequest(BaseModel):
    installation_id: str = Field(min_length=16, max_length=200)
    device_secret: str = Field(min_length=32, max_length=500)


class DriverBiometricStatusRequest(BaseModel):
    biometric_enabled: bool
