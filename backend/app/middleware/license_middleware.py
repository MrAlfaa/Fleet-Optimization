from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.deployment_controls import evaluate_license
from app.utils.response import error_response


class LicenseEnforcementMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method == "OPTIONS" or _is_diagnostic_path(request.url.path):
            return await call_next(request)

        license_status = evaluate_license(
            enabled=settings.license_enforcement_enabled,
            customer_name=settings.license_customer_name,
            expires_at=settings.license_expires_at,
            support_message=settings.license_support_message,
        )
        if not license_status.blocked:
            return await call_next(request)

        error_code = (
            "LICENSE_EXPIRED"
            if license_status.status == "expired"
            else "LICENSE_CONFIGURATION_ERROR"
        )
        return error_response(
            license_status.support_message,
            data=license_status.to_dict(),
            status_code=423,
            code=error_code,
        )


def _is_diagnostic_path(path: str) -> bool:
    public_paths = {
        "/",
        f"{settings.api_prefix}/health",
        f"{settings.api_prefix}/health/db",
        f"{settings.api_prefix}/health/license",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    return path in public_paths
