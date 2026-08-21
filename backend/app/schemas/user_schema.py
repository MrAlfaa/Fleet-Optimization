from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.utils.validators import validate_email_address, validate_password_strength, validate_user_role


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: str
    password: str
    role: str
    phone: str | None = Field(default=None, max_length=30)
    is_active: bool = True
    is_verified: bool = True

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name is required")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return validate_email_address(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        return validate_user_role(value)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = None
    role: str | None = None
    phone: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None
    is_verified: bool | None = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_user_role(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_email_address(value)


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    phone: str | None = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None


class UserListResponse(BaseModel):
    items: list[UserResponse]
    page: int
    limit: int
    total: int
    pages: int


class UserPermissionUpdate(BaseModel):
    permissions: list[str] = Field(default_factory=list)
