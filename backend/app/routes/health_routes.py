from fastapi import APIRouter

from app.core.config import settings
from app.core.database import ping_database
from app.core.deployment_controls import evaluate_license
from app.utils.response import success_response


root_router = APIRouter(tags=["Health"])
api_router = APIRouter(prefix="/health", tags=["Health"])


@root_router.get("/")
async def root() -> dict:
    return success_response(
        message="Fleet Optimization API is running",
        service=settings.app_name,
        version=settings.app_version,
        data={"environment": settings.environment},
    )


@api_router.get("")
async def health_check() -> dict:
    return success_response(
        message="Fleet Optimization API is running",
        service=settings.app_name,
        version=settings.app_version,
        data={"environment": settings.environment},
    )


@api_router.get("/db")
async def database_health_check() -> dict:
    db_status = await ping_database()
    message = "Database connection is healthy"

    if db_status["status"] == "not_configured":
        message = "Database not configured. Set MONGODB_URI to enable MongoDB Atlas connectivity."
    elif not db_status["connected"]:
        message = "Database connection is not available"

    return success_response(
        message=message,
        data=db_status,
    )


@api_router.get("/license")
async def license_health_check() -> dict:
    license_status = evaluate_license(
        enabled=settings.license_enforcement_enabled,
        customer_name=settings.license_customer_name,
        expires_at=settings.license_expires_at,
        support_message=settings.license_support_message,
    )
    return success_response(
        message="Deployment access status retrieved",
        data=license_status.to_dict(),
    )
