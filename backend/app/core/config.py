from functools import lru_cache
from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI Driven Fleet Optimization API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")

    mongodb_uri: str = Field(default="", alias="MONGODB_URI")
    mongodb_db_name: str = Field(default="fleet_optimization", alias="MONGODB_DB_NAME")
    mongodb_target_validation_enabled: bool = Field(
        default=False,
        alias="MONGODB_TARGET_VALIDATION_ENABLED",
    )
    allowed_mongodb_hosts: Annotated[list[str], NoDecode] = Field(
        default=[],
        alias="ALLOWED_MONGODB_HOSTS",
    )
    allowed_mongodb_databases: Annotated[list[str], NoDecode] = Field(
        default=[],
        alias="ALLOWED_MONGODB_DATABASES",
    )

    license_enforcement_enabled: bool = Field(default=False, alias="LICENSE_ENFORCEMENT_ENABLED")
    license_customer_name: str = Field(
        default="FleetOpt Research Deployment",
        alias="LICENSE_CUSTOMER_NAME",
    )
    license_expires_at: datetime | None = Field(default=None, alias="LICENSE_EXPIRES_AT")
    license_support_message: str = Field(
        default="The configured research access period has ended. Contact the project developer.",
        alias="LICENSE_SUPPORT_MESSAGE",
    )

    jwt_secret_key: str = Field(default="replace-with-strong-secret-key", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    osrm_base_url: str = Field(default="https://router.project-osrm.org", alias="OSRM_BASE_URL")
    branch_name: str = Field(default="Colombo Central Branch", alias="BRANCH_NAME")
    branch_address: str = Field(default="Colombo Central Branch, Colombo, Sri Lanka", alias="BRANCH_ADDRESS")
    branch_latitude: float = Field(default=6.9271, alias="BRANCH_LATITUDE")
    branch_longitude: float = Field(default=79.8612, alias="BRANCH_LONGITUDE")

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        alias="CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return [
                "http://localhost:5173",
                "http://localhost:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:3000",
            ]
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return value
        raise ValueError("CORS_ORIGINS must be a comma-separated string or list")

    @field_validator("allowed_mongodb_hosts", "allowed_mongodb_databases", mode="before")
    @classmethod
    def parse_allowlist(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return value
        raise ValueError("MongoDB allowlists must be comma-separated strings or lists")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
