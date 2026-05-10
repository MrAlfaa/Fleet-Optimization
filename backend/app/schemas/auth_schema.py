from pydantic import BaseModel, Field, field_validator

from app.utils.validators import validate_email_address, validate_password_strength, validate_user_role


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return validate_email_address(value)


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: str
    password: str
    role: str
    phone: str | None = Field(default=None, max_length=30)

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


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


class CurrentUserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    phone: str | None = None
    is_active: bool
    is_verified: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: CurrentUserResponse
