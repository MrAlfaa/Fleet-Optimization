from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.models.alert_model import ensure_alert_indexes
from app.models.demand_model import ensure_demand_indexes
from app.models.delivery_model import ensure_delivery_indexes
from app.models.driver_device_model import ensure_driver_device_indexes
from app.models.driver_execution_model import ensure_driver_execution_indexes
from app.models.maintenance_model import ensure_maintenance_indexes
from app.models.predictive_model import ensure_prediction_indexes
from app.models.route_model import ensure_route_indexes
from app.models.trip_model import ensure_trip_indexes
from app.models.user_model import ensure_user_indexes
from app.models.vehicle_model import ensure_vehicle_indexes
from app.models.vehicle_part_model import ensure_vehicle_part_indexes
from app.routes.alert_routes import router as alert_router
from app.routes.auth_routes import router as auth_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.demand_routes import router as demand_router
from app.routes.delivery_routes import router as delivery_router
from app.routes.driver_routes import router as driver_router
from app.routes.driver_device_routes import router as driver_device_router
from app.routes.health_routes import api_router as health_api_router
from app.routes.health_routes import root_router
from app.routes.live_trip_routes import router as live_trip_router
from app.routes.intelligence_routes import router as intelligence_router
from app.routes.maintenance_routes import router as maintenance_router
from app.routes.operational_routes import router as operational_router
from app.routes.predictive_routes import router as predictive_router
from app.routes.route_routes import router as route_router
from app.routes.report_routes import router as report_router
from app.routes.user_routes import router as user_router
from app.routes.vehicle_routes import router as vehicle_router
from app.utils.response import error_response
from app.services.vehicle_media_service import MEDIA_ROOT


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await connect_to_mongo()
    await ensure_user_indexes()
    await ensure_vehicle_indexes()
    await ensure_vehicle_part_indexes()
    await ensure_maintenance_indexes()
    await ensure_alert_indexes()
    await ensure_prediction_indexes()
    await ensure_demand_indexes()
    await ensure_delivery_indexes()
    await ensure_driver_device_indexes()
    await ensure_driver_execution_indexes()
    await ensure_route_indexes()
    await ensure_trip_indexes()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_ROOT), name="media")

app.include_router(root_router)
app.include_router(health_api_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(user_router, prefix=settings.api_prefix)
app.include_router(vehicle_router, prefix=settings.api_prefix)
app.include_router(maintenance_router, prefix=settings.api_prefix)
app.include_router(alert_router, prefix=settings.api_prefix)
app.include_router(dashboard_router, prefix=settings.api_prefix)
app.include_router(predictive_router, prefix=settings.api_prefix)
app.include_router(demand_router, prefix=settings.api_prefix)
app.include_router(delivery_router, prefix=settings.api_prefix)
app.include_router(route_router, prefix=settings.api_prefix)
app.include_router(driver_router, prefix=settings.api_prefix)
app.include_router(driver_device_router, prefix=settings.api_prefix)
app.include_router(live_trip_router, prefix=settings.api_prefix)
app.include_router(intelligence_router, prefix=settings.api_prefix)
app.include_router(operational_router, prefix=settings.api_prefix)
app.include_router(report_router, prefix=settings.api_prefix)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return error_response(str(exc.detail), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    validation_errors = [
        {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
            "input": error.get("input"),
        }
        for error in exc.errors()
    ]
    return error_response("Validation error", data=validation_errors, status_code=422)
