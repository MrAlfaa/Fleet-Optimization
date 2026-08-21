from fastapi import APIRouter, Depends, Request

from app.middleware.auth_middleware import require_roles
from app.schemas.driver_device_schema import DriverBiometricStatusRequest, DriverDeviceEnrollRequest, DriverDeviceSessionRequest
from app.services.driver_device_service import create_driver_device_session, enroll_driver_device, revoke_current_device, update_biometric_indicator
from app.utils.response import success_response


router = APIRouter(prefix="/driver-device", tags=["Driver Device"])


@router.post("/enroll")
async def enroll(payload: DriverDeviceEnrollRequest) -> dict:
    return success_response("Driver device enrolled successfully", data=await enroll_driver_device(payload.model_dump()))


@router.post("/session")
async def session(payload: DriverDeviceSessionRequest) -> dict:
    return success_response("Driver device session created successfully", data=await create_driver_device_session(payload.model_dump()))


@router.post("/logout")
async def logout(request: Request, user: dict = Depends(require_roles(["driver"]))) -> dict:
    from app.core.security import decode_access_token
    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    payload = decode_access_token(token)
    await revoke_current_device(user, payload["device_id"])
    return success_response("Driver device logged out successfully", data={"revoked": True})


@router.get("/status")
async def device_status(user: dict = Depends(require_roles(["driver"]))) -> dict:
    return success_response("Driver device is active", data={"active": True, "driver": user})


@router.patch("/biometric")
async def biometric_status(payload: DriverBiometricStatusRequest, request: Request, user: dict = Depends(require_roles(["driver"]))) -> dict:
    from app.core.security import decode_access_token
    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    claims = decode_access_token(token)
    await update_biometric_indicator(user, claims["device_id"], payload.biometric_enabled)
    return success_response("Biometric preference updated", data={"biometric_enabled": payload.biometric_enabled})
